import { Alert, Empty, Skeleton } from 'antd'
import { useParams } from 'react-router-dom'
import { useState } from 'react'
import { getApiMetadata, listApis } from '../api/metadata'
import { ApiCatalogOverview } from '../features/api-catalog/ApiCatalogOverview'
import { ApiDetailDocument } from '../features/api-catalog/ApiDetailDocument'
import { useAsyncData } from '../hooks/useAsyncData'

export function ApiCatalogPage() {
  const { apiName } = useParams()
  const [metadataVersion, setMetadataVersion] = useState(0)
  const apiListState = useAsyncData((signal) => listApis(signal), [])
  const detailState = useAsyncData(
    (signal) => (apiName ? getApiMetadata(apiName, signal) : Promise.resolve(null)),
    [apiName, metadataVersion],
  )

  if (!apiName) {
    return <ApiCatalogOverview apis={apiListState.data} loading={apiListState.loading} error={apiListState.error} />
  }

  return <main className="api-detail page-enter">
    {detailState.loading && <div className="detail-loading"><Skeleton active paragraph={{ rows: 12 }} /></div>}
    {detailState.error && <Alert type="error" showIcon message="接口详情加载失败" description={detailState.error.message} />}
    {!detailState.loading && !detailState.error && !detailState.data && <Empty description="请选择一个接口" />}
    {detailState.data && <ApiDetailDocument detail={detailState.data} onMetadataChanged={() => setMetadataVersion((value) => value + 1)} />}
  </main>
}
