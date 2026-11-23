const dialog = document.getElementById('lecture-poster-dialog');
const closeButton = document.getElementById('lecture-poster-close');
const thumbnail = document.querySelector('.lecture-poster-thumbnail');
let opener;

function updateLabels() {
  const english = document.documentElement.lang === 'en';
  dialog.setAttribute('aria-label', english ? 'Full poster for the distinguished lecture by Zaiwen Wen' : '文再文大师讲堂完整海报');
  closeButton.setAttribute('aria-label', english ? 'Close poster' : '关闭海报');
  thumbnail.setAttribute('aria-label', english ? 'View full poster for the distinguished lecture by Zaiwen Wen' : '查看文再文大师讲堂完整海报');
}

for (const button of [thumbnail, document.querySelector('.lecture-poster-open')]) {
  button.addEventListener('click', () => {
    opener = button;
    dialog.showModal();
  });
}
closeButton.addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => opener?.focus({ preventScroll: true }));
dialog.addEventListener('click', event => {
  if (event.target === dialog) dialog.close();
});
// The poster has only one interactive control; keep Tab and Shift+Tab on it.
dialog.addEventListener('keydown', event => {
  if (event.key === 'Tab') {
    event.preventDefault();
    closeButton.focus();
  }
});
document.addEventListener('ai4s-language-change', updateLabels);
updateLabels();

// After the lecture ends, mark the announcement as past so it stops reading like an upcoming event.
const announcement = document.getElementById('lecture-announcement');
const endsAt = Date.parse(announcement?.dataset.endsAt ?? '');
if (announcement && Number.isFinite(endsAt)) {
  const setText = (element, zh, en) => {
    element.querySelector('.lang-zh').textContent = zh;
    element.querySelector('.lang-en').textContent = en;
  };
  const markPast = () => {
    if (Date.now() < endsAt || announcement.classList.contains('is-past')) return;
    announcement.classList.add('is-past');
    setText(announcement.querySelector('.lecture-announcement-label'), '往期大师讲堂', 'Past distinguished lecture');
    setText(announcement.querySelector('.lecture-preview-link'), '查看详情 ↗', 'Read details ↗');
  };
  markPast();
  document.addEventListener('visibilitychange', markPast);
}
