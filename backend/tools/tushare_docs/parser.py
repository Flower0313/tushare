from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any


def normalize_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


class _NavigationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_nav = False
        self.nav_depth = 0
        self.stack: list[dict[str, Any]] = []
        self.roots: list[dict[str, Any]] = []
        self.capture_link = False
        self.link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "nav":
            self.in_nav = True
            self.nav_depth = 1
            return
        if not self.in_nav:
            return
        if tag == "nav":
            self.nav_depth += 1
        elif tag == "li":
            self.stack.append({"title": "", "href": "", "children": []})
        elif tag == "a" and self.stack:
            href = attributes.get("href") or ""
            if "/document/2?doc_id=" in href:
                self.stack[-1]["href"] = href
                self.capture_link = True
                self.link_text = []

    def handle_endtag(self, tag: str) -> None:
        if not self.in_nav:
            return
        if tag == "a" and self.capture_link:
            if self.stack:
                self.stack[-1]["title"] = normalize_text("".join(self.link_text))
            self.capture_link = False
        elif tag == "li" and self.stack:
            node = self.stack.pop()
            if not node["title"]:
                return
            if self.stack:
                self.stack[-1]["children"].append(node)
            else:
                self.roots.append(node)
        elif tag == "nav":
            self.nav_depth -= 1
            if self.nav_depth <= 0:
                self.in_nav = False

    def handle_data(self, data: str) -> None:
        if self.capture_link:
            self.link_text.append(data)


class _ContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_content = False
        self.content_div_depth = 0
        self.title = ""
        self.paragraphs: list[str] = []
        self.tables: list[dict[str, Any]] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._table: dict[str, Any] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div" and not self.in_content:
            classes = set((attributes.get("class") or "").split())
            if "content" in classes:
                self.in_content = True
                self.content_div_depth = 1
                return
        elif self.in_content and tag == "div":
            self.content_div_depth += 1
        if not self.in_content:
            return
        if tag == "h2" and not self.title:
            self._capture = "h2"
            self._buffer = []
        elif tag == "p":
            self._capture = "p"
            self._buffer = []
        elif tag == "br" and self._capture:
            self._buffer.append("\n")
        elif tag == "table":
            self._table = {
                "marker": self.paragraphs[-1] if self.paragraphs else "",
                "rows": [],
            }
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self.in_content:
            return
        if tag == "h2" and self._capture == "h2":
            self.title = normalize_text("".join(self._buffer))
            self._capture = None
        elif tag == "p" and self._capture == "p":
            text = normalize_text("".join(self._buffer))
            if text:
                self.paragraphs.append(text)
            self._capture = None
        elif tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(normalize_text("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag == "div":
            self.content_div_depth -= 1
            if self.content_div_depth <= 0:
                self.in_content = False

    def handle_data(self, data: str) -> None:
        if not self.in_content:
            return
        if self._cell is not None:
            self._cell.append(data)
        if self._capture is not None:
            self._buffer.append(data)


class TushareDocumentParser:
    STOCK_SUBCATEGORIES = (
        "基础数据",
        "行情数据",
        "财务数据",
        "参考数据",
        "特色数据",
        "两融及转融通",
        "资金流向数据",
        "打板专题数据",
    )

    def parse_inventory(self, html: str, base_url: str) -> list[dict[str, str]]:
        parser = _NavigationParser()
        parser.feed(html)
        stock = self._find_node(parser.roots, "股票数据")
        if stock is None:
            raise ValueError("股票数据目录未找到")
        inventory: list[dict[str, str]] = []
        for subcategory in stock["children"]:
            if subcategory["title"] not in self.STOCK_SUBCATEGORIES:
                continue
            for api in subcategory["children"]:
                match = re.search(r"doc_id=(\d+)", api["href"])
                if not match:
                    continue
                inventory.append(
                    {
                        "category": "股票数据",
                        "subcategory": subcategory["title"],
                        "title": api["title"],
                        "doc_id": match.group(1),
                        "documentation_url": f"{base_url}?doc_id={match.group(1)}",
                    }
                )
        return inventory

    def parse_api_page(self, html: str) -> dict[str, Any]:
        parser = _ContentParser()
        parser.feed(html)
        text = "\n".join(parser.paragraphs)
        api_match = re.search(r"(?:接口|接口名|API)[：:]\s*([A-Za-z][A-Za-z0-9_]*)", text)
        description = self._label_value(text, ("描述", "接口描述"))
        request_limit = self._label_value(text, ("限量", "调用限制", "数据量"))
        permission = self._label_value(text, ("权限", "积分"))
        update_frequency = self._find_update_frequency(parser.paragraphs)
        input_rows: list[list[str]] = []
        output_rows: list[list[str]] = []
        for table in parser.tables:
            rows = table["rows"]
            if not rows:
                continue
            headers = [value.lower() for value in rows[0]]
            marker = str(table["marker"])
            if (
                "默认显示" in rows[0]
                or "输出参数" in marker
                or "输出字段" in marker
                or "输出指标" in marker
            ):
                output_rows = rows[1:]
            elif "必选" in rows[0] or "输入参数" in marker or "接口参数" in marker:
                input_rows = rows[1:]
            elif "名称" in rows[0] and "类型" in rows[0] and "required" in headers:
                input_rows = rows[1:]

        params = [self._parse_param(row, index) for index, row in enumerate(input_rows, 1)]
        fields = [self._parse_field(row, index) for index, row in enumerate(output_rows, 1)]
        row_limit = self._parse_row_limit(request_limit or text)
        rate_limit = self._parse_rate_limit(permission or text)
        points = self._parse_points(permission or text)
        return {
            "api_name": api_match.group(1) if api_match else "",
            "api_title": parser.title,
            "description": description
            or (parser.paragraphs[0] if parser.paragraphs else parser.title),
            "permission_description": permission,
            "request_limit": request_limit,
            "update_frequency": update_frequency,
            "data_description": "\n\n".join(parser.paragraphs[:4]),
            "points_required": points,
            "row_limit": row_limit,
            "rate_limit": rate_limit,
            "params": params,
            "fields": fields,
        }

    @classmethod
    def _find_node(cls, nodes: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
        for node in nodes:
            if node["title"] == title:
                return node
            found = cls._find_node(node["children"], title)
            if found:
                return found
        return None

    @staticmethod
    def _label_value(text: str, labels: tuple[str, ...]) -> str | None:
        for label in labels:
            match = re.search(rf"(?:^|\n){re.escape(label)}[：:]\s*([^\n]+)", text)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _find_update_frequency(paragraphs: list[str]) -> str | None:
        for paragraph in paragraphs:
            for line in paragraph.splitlines():
                if any(term in line for term in ("更新时间", "更新频率", "更新：", "数据更新")):
                    return re.sub(r"^[^：:]+[：:]", "", line).strip()
        return None

    @staticmethod
    def _parse_param(row: list[str], position: int) -> dict[str, Any]:
        padded = (row + ["", "", "", ""])[:4]
        name, data_type, required, description = padded
        date_like = bool(re.search(r"(?:date|日期|YYYYMMDD)", f"{name} {description}", re.I))
        default_match = re.search(r"默认(?:是|为)?\s*([A-Za-z0-9_.-]+)", description)
        return {
            "name": name.strip(),
            "type": (data_type.strip() or "str").lower(),
            "required": required.strip().upper() in {"Y", "YES", "是", "必选"},
            "description": description.strip(),
            "format": "YYYYMMDD" if date_like else None,
            "input_kind": "date" if date_like else "text",
            "enum_values": [],
            "default_value": default_match.group(1) if default_match else None,
            "constraints": {},
            "position": position,
        }

    @staticmethod
    def _parse_field(row: list[str], position: int) -> dict[str, Any]:
        padded = (row + ["", "", "", ""])[:4]
        name, data_type, default, description = padded
        return {
            "name": name.strip(),
            "type": (data_type.strip() or "str").lower(),
            "default": default.strip().upper() not in {"N", "NO", "否"},
            "description": description.strip(),
            "position": position,
        }

    @staticmethod
    def _parse_points(text: str) -> int | None:
        values = [int(value) for value in re.findall(r"(\d+)\s*积分", text)]
        return min(values) if values else None

    @staticmethod
    def _parse_row_limit(text: str) -> int | None:
        patterns = (
            r"(?:最多返回|最大返回|单次[^，。；]*?)(\d{3,})\s*行",
            r"(?:限量|上限)[^\d]*(\d{3,})\s*条",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _parse_rate_limit(text: str) -> dict[str, int]:
        match = re.search(r"每分钟(?:最多)?(?:请求|调用)?\s*(\d+)\s*次", text)
        if not match:
            match = re.search(r"每分钟\s*(\d+)\s*次", text)
        return {"requests": int(match.group(1)), "period_seconds": 60} if match else {}
