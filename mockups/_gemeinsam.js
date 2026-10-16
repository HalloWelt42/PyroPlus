/* Kleine Durchklick-Interaktivität für die Mockups: Reiter, Segmente und Chips umschalten. */
document.addEventListener('DOMContentLoaded', () => {
  const name = document.body.dataset.seite || location.pathname.split('/').pop();
  const marke = document.querySelector('.mock-name');
  if (marke) marke.textContent = 'Mockup: ' + name;
  for (const gruppe of document.querySelectorAll('.segment, .reiter, .chips, .kategorien')) {
    gruppe.addEventListener('click', (e) => {
      const ziel = e.target.closest('button');
      if (!ziel || ziel.querySelector('.x') === e.target) return;
      for (const b of gruppe.querySelectorAll('button')) b.classList.remove('active');
      ziel.classList.add('active');
    });
  }
  for (const r of document.querySelectorAll('.regler input[type="range"]')) {
    r.addEventListener('input', () => { const w = r.parentElement.querySelector('.wert'); if (w) w.textContent = r.value; });
  }
});
