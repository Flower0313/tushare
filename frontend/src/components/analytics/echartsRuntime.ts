import * as echarts from 'echarts/core'
import { BarChart, CandlestickChart, FunnelChart, LineChart, PieChart, ScatterChart, TreemapChart } from 'echarts/charts'
import { DataZoomComponent, DatasetComponent, GridComponent, LegendComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, CandlestickChart, FunnelChart, LineChart, PieChart, ScatterChart, TreemapChart,
  DataZoomComponent, DatasetComponent, GridComponent, LegendComponent, TooltipComponent,
  VisualMapComponent, CanvasRenderer,
])

export { echarts }
