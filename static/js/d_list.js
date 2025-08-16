const submit = document.getElementById('submit');
const list1 = document.getElementById('dl_list_1');
const list2 = document.getElementById('dl_list_2');
const to_1 = document.getElementById('dl_to_1');
const to_2 = document.getElementById('dl_to_2');
const allTo_1 = document.getElementById('dl_all_to_1');
const allTo_2 = document.getElementById('dl_all_to_2');
const count1 = document.getElementById('dl_count_1');
const count2 = document.getElementById('dl_count_2');

function sortByValue(list) {
  [...list.children].sort((a, b) => Number(a.value) - Number(b.value)).forEach(elem => list.appendChild(elem));
}

function countRefresh() {
  count1.textContent = list1.length;
  count2.textContent = list2.length;
}

countRefresh();
submit.addEventListener('click', () => {
  [...list1.children].forEach(elem => elem.selected = false);
  [...list2.children].forEach(elem => elem.selected = true);
});

allTo_1.addEventListener('click', () => {
  [...list1.children].forEach(elem => elem.selected = false);
  [...list2.children].forEach(elem => { list1.appendChild(elem); elem.selected = true});
  sortByValue(list1);
  countRefresh();
});

allTo_2.addEventListener('click', () => {
  [...list2.children].forEach(elem => elem.selected = false);
  [...list1.children].forEach(elem => { list2.appendChild(elem); elem.selected = true; });
  sortByValue(list2);
  countRefresh();
});

to_1.addEventListener('click', () => {
  [...list1.children].forEach(elem => elem.selected = false);
  [...list2.children].filter(elem => elem.selected).forEach(elem => list1.appendChild(elem));
  sortByValue(list1);
  countRefresh();
});

to_2.addEventListener('click', () => {
  [...list2.children].forEach(elem => elem.selected = false);
  [...list1.children].filter(elem => elem.selected).forEach(elem => list2.appendChild(elem));
  sortByValue(list2);
  countRefresh();
});
