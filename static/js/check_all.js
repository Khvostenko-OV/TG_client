const savePages = {'Parsers list': 'taskChecked', }
const main = document.getElementById('ca_main');
const count = document.getElementById('ca_counter');
const boxes = [...document.querySelectorAll('.ca_checkbox')]

function saveState() {
  if (!(document.title in savePages)) return;
  const state = boxes.filter(obj => {return obj.checked}).map(obj => {return obj.value});
  localStorage.setItem(savePages[document.title], JSON.stringify(state));
}

function loadState() {
  if (!(document.title in savePages)) return;
  const state = JSON.parse(localStorage.getItem(savePages[document.title]));
  if (state === null) return;
  [...document.querySelectorAll('a, button')].forEach(elem => elem.addEventListener('click', () => {
    localStorage.setItem(savePages[document.title], '[]');
  }));
  boxes.forEach(elem => elem.checked = state.includes(elem.value));
  main.checked = boxes.length === state.length;
}

loadState();
count.textContent = boxes.reduce((sum, elem) => sum + elem.checked, 0);

main.addEventListener('change', () => {
  boxes.forEach(elem => elem.checked = main.checked);
  count.textContent = main.checked? boxes.length : 0;
  saveState();
});

boxes.forEach(elem => elem.addEventListener('change', () => {
  elem.checked? count.textContent++ : count.textContent--;
  main.checked = boxes.length === Number(count.textContent);
  saveState();
}));
