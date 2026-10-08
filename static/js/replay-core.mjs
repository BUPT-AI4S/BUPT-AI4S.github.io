export function formatTime(ms) {
  if (!Number.isFinite(ms)) return '—';
  const n=Math.max(0,Math.floor(ms/1000)), h=Math.floor(n/3600), m=Math.floor(n/60)%60, s=n%60;
  return (h ? `${h}:${String(m).padStart(2,'0')}` : String(m))+':'+String(s).padStart(2,'0');
}
export function activeSegment(rows, ms) { return rows.findIndex(r=>Number.isFinite(r.start)&&Number.isFinite(r.end)&&r.start<=ms&&ms<r.end); }
export function findMatches(rows, query) {
  const q=query.trim().toLowerCase(); if(!q)return [];
  return rows.flatMap((r,index)=>{const text=r.text.toLowerCase(), hits=[];let from=0,pos;
    while((pos=text.indexOf(q,from))!==-1){hits.push({index,start:pos,end:pos+q.length});from=pos+q.length;}return hits;});
}

const isMasterclass = course => course.id.startsWith('chairs-') || course.title.includes('大师讲堂');

export function sortCourses(courses) {
  return [...courses].sort((a,b) => Number(isMasterclass(a))-Number(isMasterclass(b))
    || a.id.localeCompare(b.id, 'en', {numeric:true}));
}

export function courseLabels(courses) {
  const counts = { '课程': 0, '大师讲堂': 0 };
  return courses.map(course => {
    const label = isMasterclass(course) ? '大师讲堂' : '课程';
    return {label, number: String(++counts[label]).padStart(2, '0')};
  });
}
