async function operator(proxies = [], targetPlatform, context) {
  const SUBS_KEY = 'subs'
  const COLLECTIONS_KEY = 'collections'
  const $ = $substore
  const { source } = context
  const { _collection: collection } = source

  if (!collection || Object.keys(source).length > 1) throw new Error('暂时仅支持组合订阅, 请在组合订阅中使用此脚本')

  let extraGB = 0
  if (typeof $arguments !== 'undefined' && $arguments.extra) {
    extraGB = parseFloat($arguments.extra)
  }
  const GB_IN_BYTES = 1024 * 1024 * 1024
  const extraBytes = extraGB * GB_IN_BYTES

  const allSubs = $.read(SUBS_KEY) || []
  let uploadSum = 0
  let downloadSum = 0
  let totalSum = 0
  let expire

  const { parseFlowHeaders, getFlowHeaders, normalizeFlowHeader } = flowUtils

  const subnames = [...collection.subscriptions]
  let subscriptionTags = collection.subscriptionTags

  if (Array.isArray(subscriptionTags) && subscriptionTags.length > 0) {
    allSubs.forEach(sub => {
      if (
        Array.isArray(sub.tag) &&
        sub.tag.length > 0 &&
        !subnames.includes(sub.name) &&
        sub.tag.some(tag => subscriptionTags.includes(tag))
      ) {
        subnames.push(sub.name)
      }
    })
  }

  for await (const sub of allSubs) {
    if (subnames.includes(sub.name)) {
      let subInfo
      let flowInfo

      if (sub.source !== 'local' || ['localFirst', 'remoteFirst'].includes(sub.mergeSources)) {
        try {
          let url = `${sub.url}`.split(/[\r\n]+/).map(i => i.trim()).filter(i => i.length)?.[0] || ''
          let subArgs = {}
          const rawArgs = url.split('#')
          url = url.split('#')[0]

          if (rawArgs.length > 1) {
            try {
              subArgs = JSON.parse(decodeURIComponent(rawArgs[1]))
            } catch (e) {
              for (const pair of rawArgs[1].split('&')) {
                const key = pair.split('=')[0]
                const value = pair.split('=')[1]
                subArgs[key] = value == null || value === '' ? true : decodeURIComponent(value)
              }
            }
          }

          if (!subArgs.noFlow && /^https?/.test(url)) {
            flowInfo = await getFlowHeaders(
              subArgs?.insecure ? `${url}#insecure` : url,
              subArgs.flowUserAgent,
              undefined,
              sub.proxy,
              subArgs.flowUrl
            )
            if (flowInfo) {
              const headers = normalizeFlowHeader(flowInfo, true)
              if (headers?.['subscription-userinfo']) {
                subInfo = headers['subscription-userinfo']
              }
            }
          }
        } catch (err) {
          $.error(`订阅 ${sub.name} 获取流量实时信息失败: ${err.message}`)
        }
      }

      if (sub.subUserinfo) {
        let subUserInfoStr
        if (/^https?:\/\//.test(sub.subUserinfo)) {
          try {
            subUserInfoStr = await getFlowHeaders(undefined, undefined, undefined, sub.proxy, sub.subUserinfo)
          } catch (e) {
            $.error(`订阅 ${sub.name} 流量链接访问失败`)
          }
        } else {
          subUserInfoStr = sub.subUserinfo
        }

        const headers = normalizeFlowHeader([subUserInfoStr, flowInfo].filter(i => i).join(';'), true)
        if (headers?.['subscription-userinfo']) {
          subInfo = headers['subscription-userinfo']
        }
      }

      if (subInfo) {
        const { total, usage: { upload, download }, expires } = parseFlowHeaders(subInfo)
        if (upload > 0) uploadSum += upload
        if (download > 0) downloadSum += download
        if (total > 0) totalSum += total
        if (expires && expires * 1000 > Date.now()) {
          expire = expire ? Math.min(expire, expires) : expires
        }
      }
    }
  }

  const finalTotalSum = totalSum + extraBytes

  const subUserInfo = `upload=${uploadSum}; download=${downloadSum}; total=${finalTotalSum}${
    expire ? ` ; expire=${expire}` : ''
  }`

  const allCols = $.read(COLLECTIONS_KEY) || []
  for (var index = 0; index < allCols.length; index++) {
    if (collection.name === allCols[index].name) {
      allCols[index].subUserinfo = subUserInfo
      break
    }
  }
  $.write(allCols, COLLECTIONS_KEY)

  if (typeof $options !== 'undefined' && $options) {
    $options._res = {
      headers: {
        'subscription-userinfo': subUserInfo,
      },
    }
  }

  return proxies
}
