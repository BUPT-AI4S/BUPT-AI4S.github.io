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
  const source=sourceUrl(value);
  if(!source)return '';
  const url=new URL(source);url.hash='view=FitH';return url.href;
}
