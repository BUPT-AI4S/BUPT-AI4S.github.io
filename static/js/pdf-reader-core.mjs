function sourceUrl(value) {
  try {
    const url=new URL(value);
    return url.protocol==='https:'&&!url.username&&!url.password?url.href:'';
  } catch {return '';}
}
export function pdfSourceLinks(paper) {
  return {pdf:sourceUrl(paper?.pdfUrl),paper:sourceUrl(paper?.paperUrl)||sourceUrl(paper?.forumUrl)};
}
export function nativePdfSource(value) {
  return sourceUrl(value);
}
export function openNativePdf(value,browser=window) {
  const source=nativePdfSource(value);
  if(!source)return false;
  try {
    if(browser.parent===browser)browser.location.replace(source);
    else browser.top.location.assign(source);
    return true;
  } catch {return false;}
}
