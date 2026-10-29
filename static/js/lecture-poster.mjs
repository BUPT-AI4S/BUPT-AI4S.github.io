const dialog = document.getElementById('lecture-poster-dialog');
const closeButton = document.getElementById('lecture-poster-close');
const thumbnail = document.querySelector('.lecture-poster-thumbnail');
let opener;

function updateLabels() {
  const english = document.documentElement.lang === 'en';
  dialog.setAttribute('aria-label', english ? 'Full poster for the expert talk by Haochen Li' : '李昊辰专家报告完整海报');
  closeButton.setAttribute('aria-label', english ? 'Close poster' : '关闭海报');
  thumbnail.setAttribute('aria-label', english ? 'View full poster for the expert talk by Haochen Li' : '查看李昊辰专家报告完整海报');
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
