import { ApiNavigation } from '../../components/ApiNavigation'
import type { ApiMetadataSummary } from '../../types/metadata'

interface Props {
  apis: ApiMetadataSummary[] | null
  loading: boolean
  error: Error | null
}

export function ApiCatalogOverview({ apis, loading, error }: Props) {
  return <main className="catalog-page page-enter">
    <header className="catalog-page__heading">
      <div><span className="page-kicker">数据采集</span><h1>API 目录</h1><p>在一个 Metadata 驱动的目录中浏览、检索并运行已注册的 Tushare 接口。</p></div>
      <div className="catalog-page__metric"><strong>{apis?.length ?? '—'}</strong><span>已注册 API</span></div>
    </header>
    <ApiNavigation apis={apis} loading={loading} error={error} />
  </main>
}
