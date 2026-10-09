let { type, name, outbound, includeUnsupportedProxy, url } = $arguments

type = /^1$|col|组合/i.test(type) ? 'collection' : 'subscription'

const parser = ProxyUtils.JSON5 || JSON
let config
try {
  config = parser.parse($content ?? $files[0])
} catch (e) {
  throw new Error(`配置文件格式错误: ${e.message ?? e}`)
}

let proxies
if (url) {
  proxies = await produceArtifact({
    name,
    type,
    platform: 'sing-box',
    produceType: 'internal',
    produceOpts: {
      'include-unsupported-proxy': includeUnsupportedProxy,
    },
    subscription: {
      name,
      url,
      source: 'remote',
    },
  })
} else {
  proxies = await produceArtifact({
    name,
    type,
    platform: 'sing-box',
    produceType: 'internal',
    produceOpts: {
      'include-unsupported-proxy': includeUnsupportedProxy,
    },
  })
}

const outboundsRules = outbound
  .split('🕳')
  .filter(i => i)
  .map(i => {
    let [outboundPattern, tagPattern = '.*'] = i.split('🏷')
    const tagRegex = createTagRegExp(tagPattern)
    return [createOutboundRegExp(outboundPattern), tagRegex]
  })

config.outbounds.map(outbound => {
  let uniqueTags = new Set(outbound.outbounds || [])
  
  outboundsRules.map(([outboundRegex, tagRegex]) => {
    if (outboundRegex.test(outbound.tag)) {
      const tags = getTags(proxies, tagRegex)
      tags.forEach(tag => uniqueTags.add(tag))
    }
  })

  outbound.outbounds = Array.from(uniqueTags)
})

const compatible_outbound = {
  tag: 'COMPATIBLE',
  type: 'direct',
}

let compatibleAdded = false
config.outbounds.map(outbound => {
  const isTargeted = outboundsRules.some(([outboundRegex]) => outboundRegex.test(outbound.tag))
  
  if (isTargeted) {
      if (!outbound.outbounds || outbound.outbounds.length === 0) {
           if (!outbound.outbounds) outbound.outbounds = []
           if (!compatibleAdded) {
              config.outbounds.push(compatible_outbound)
              compatibleAdded = true
           }
           outbound.outbounds.push(compatible_outbound.tag)
      }
  }
})

config.outbounds.push(...proxies)

$content = JSON.stringify(config, null, 2)

function getTags(proxies, regex) {
  return (regex ? proxies.filter(p => regex.test(p.tag)) : proxies).map(p => p.tag)
}

function createTagRegExp(tagPattern) {
  return new RegExp(tagPattern.replace('ℹ️', ''), tagPattern.includes('ℹ️') ? 'i' : undefined)
}

function createOutboundRegExp(outboundPattern) {
  return new RegExp(outboundPattern.replace('ℹ️', ''), outboundPattern.includes('ℹ️') ? 'i' : undefined)
}