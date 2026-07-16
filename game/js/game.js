/* ============================================================
   KINDRED ATLAS — engine
   Vanilla JS + canvas. No dependencies. Saves to localStorage.
   ============================================================ */

'use strict';

const W = 960, H = 600;
const SAVE_KEY = 'kindred-atlas-save-v1';

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const hudMoney = document.getElementById('hud-money');
const hudGoods = document.getElementById('hud-goods');
const hudParty = document.getElementById('hud-party');
const hudFluency = document.getElementById('hud-fluency');
const hudCountry = document.getElementById('hud-country');
const promptEl = document.getElementById('prompt');
const toastEl = document.getElementById('toast');
const modalEl = document.getElementById('modal');
const modalBox = document.getElementById('modal-box');

/* ---------------- State ---------------- */

function defaultState() {
  return {
    money: 150,
    country: 'london',
    party: [],                    // creature ids
    befriended: {},               // id -> true
    fluency: { london: 10, usa: 0, japan: 0, india: 0 },
    goods: { london: 3, usa: 0, japan: 0, india: 0 },  // counts by ORIGIN country
    notes: [],                    // [{id,title,source,text}]
    upgrades: {},                 // id -> true
    doneScenarios: {},            // scenario id -> true
    visited: { london: true },
    intro: false,
    won: false
  };
}

let state = loadState();

function loadState() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) return Object.assign(defaultState(), JSON.parse(raw));
  } catch (e) { /* corrupted save -> fresh start */ }
  return defaultState();
}
function save() {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(state)); } catch (e) {}
}

/* ---------------- Notes / learning ---------------- */

function addNote(id, text, sourceOverride) {
  if (state.notes.some(n => n.id === id)) return false;
  const meta = FIELD_NOTES[id] || { title: id, source: sourceOverride || 'Field observation' };
  state.notes.push({ id, title: meta.title, source: sourceOverride || meta.source, text });
  save();
  toast(`\u{1F4D3} Field note added: ${meta.title}`);
  return true;
}

function addCultureNote(countryId, scenario, whyText) {
  const id = 'culture_' + scenario.id;
  if (state.notes.some(n => n.id === id)) return;
  state.notes.push({
    id,
    title: scenario.q,
    source: `Cultural fluency · ${COUNTRIES[countryId].name}`,
    text: whyText
  });
  save();
}

/* ---------------- Toast & prompt ---------------- */

let toastTimer = null;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 3200);
}

/* ---------------- Modal system ---------------- */

let modalOpen = false;
let modalChoices = [];

function showModal({ title, sub, body, choices, closable }) {
  modalOpen = true;
  modalChoices = choices || [];
  let html = '';
  if (title) html += `<h2>${title}</h2>`;
  if (sub) html += `<div class="modal-sub">${sub}</div>`;
  if (body) html += `<div class="modal-body">${body}</div>`;
  if (choices && choices.length) {
    html += '<div class="choices">';
    choices.forEach((c, i) => {
      html += `<button class="choice" data-i="${i}"><span class="key">${i + 1}</span>${c.label}</button>`;
    });
    html += '</div>';
  }
  if (closable) html += `<div class="modal-hint">Esc to close</div>`;
  modalBox.innerHTML = html;
  modalEl.classList.remove('hidden');
  modalBox.querySelectorAll('.choice').forEach(btn => {
    btn.addEventListener('click', () => pickChoice(parseInt(btn.dataset.i, 10)));
  });
  modalEl.dataset.closable = closable ? '1' : '';
}

function pickChoice(i) {
  const c = modalChoices[i];
  if (!c) return;
  closeModal();
  if (c.cb) c.cb();
}

function closeModal() {
  modalOpen = false;
  modalChoices = [];
  modalEl.classList.add('hidden');
}

/* ---------------- Utility ---------------- */

const rnd = (a, b) => a + Math.random() * (b - a);
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
function fmt(n) { return '\u{1FA99} ' + Math.round(n); }

/* ---------------- World entities ---------------- */

const player = { x: W / 2, y: H / 2 + 100, r: 14, speed: 3.1 };
let entities = [];   // creatures + npcs in current scene
let airportZone = { x: W - 190, y: H - 130, w: 150, h: 90 };

function enterCountry(id) {
  state.country = id;
  state.visited[id] = true;
  save();
  buildScene();
  const c = COUNTRIES[id];
  toast(`${c.flag} ${c.name} — “${c.welcome}”`);
  updateHUD();
}

function buildScene() {
  const cid = state.country;
  entities = [];

  // Creatures not yet befriended, spawn if fluency allows visibility (hidden ones show as "?" hint via local)
  CREATURES.filter(cr => cr.country === cid && !state.befriended[cr.id]).forEach((cr, i) => {
    entities.push({
      kind: 'creature', ref: cr,
      x: 140 + i * 260 + rnd(-40, 40), y: 170 + rnd(-30, 60),
      vx: 0, vy: 0, wanderT: 0
    });
  });

  const c = COUNTRIES[cid];
  entities.push({ kind: 'merchant', name: c.merchantName, x: 130, y: H - 150 });
  entities.push({ kind: 'local',    name: c.localName,    x: W / 2 + 40, y: H - 190 });
  entities.push({ kind: 'outfitter', name: 'The Outfitter', x: W / 2 - 180, y: H - 140 });
}

/* ---------------- Input ---------------- */

const keys = {};
window.addEventListener('keydown', (e) => {
  if (modalOpen) {
    if (e.key >= '1' && e.key <= '9') {
      const i = parseInt(e.key, 10) - 1;
      if (modalChoices[i]) { e.preventDefault(); pickChoice(i); }
    } else if (e.key === 'Escape' && modalEl.dataset.closable) {
      closeModal();
    }
    return;
  }
  keys[e.key.toLowerCase()] = true;
  if (e.key === 'e' || e.key === 'E' || e.key === 'Enter') tryInteract();
  if (e.key === 'm' || e.key === 'M') openTravelMap();
  if (e.key === 'j' || e.key === 'J') openJournal();
  if (e.key === '?' || e.key === 'h' || e.key === 'H') openHelp();
});
window.addEventListener('keyup', (e) => { keys[e.key.toLowerCase()] = false; });

document.getElementById('btn-map').addEventListener('click', () => { if (!modalOpen) openTravelMap(); });
document.getElementById('btn-journal').addEventListener('click', () => { if (!modalOpen) openJournal(); });
document.getElementById('btn-help').addEventListener('click', () => { if (!modalOpen) openHelp(); });
document.getElementById('btn-reset').addEventListener('click', () => {
  if (modalOpen) return;
  showModal({
    title: 'Start over?',
    body: 'This erases your money, Kindred and field notes. There is no undo.',
    choices: [
      { label: 'Keep my journey', cb: () => {} },
      { label: 'Erase and restart', cb: () => { localStorage.removeItem(SAVE_KEY); state = defaultState(); enterCountry('london'); showIntro(); } }
    ],
    closable: true
  });
});

/* ---------------- Interaction ---------------- */

function nearestInteractable() {
  let best = null, bestD = 62;
  for (const e of entities) {
    const d = Math.hypot(e.x - player.x, e.y - player.y);
    if (d < bestD) { best = e; bestD = d; }
  }
  return best;
}

function inAirport() {
  return player.x > airportZone.x && player.x < airportZone.x + airportZone.w &&
         player.y > airportZone.y && player.y < airportZone.y + airportZone.h;
}

function tryInteract() {
  if (inAirport()) { openTravelMap(); return; }
  const e = nearestInteractable();
  if (!e) return;
  if (e.kind === 'creature') startEncounter(e);
  else if (e.kind === 'merchant') startHaggle();
  else if (e.kind === 'local') startCulture();
  else if (e.kind === 'outfitter') openShop();
}

/* ---------------- Creature encounters (negotiation) ---------------- */

function startEncounter(ent) {
  const cr = ent.ref;
  const flu = state.fluency[state.country];
  if (cr.minFluency > flu) {
    showModal({
      title: `A shy presence…`,
      sub: cr.name,
      body: `The ${cr.name} keeps its distance. It only trusts travellers the locals vouch for.<br><br>` +
            `<b>Cultural fluency needed: ${cr.minFluency}%</b> (you have ${flu}%).<br>` +
            `Talk with ${COUNTRIES[state.country].localName} to learn the local ways.`,
      choices: [{ label: 'Understood', cb: () => {} }],
      closable: true
    });
    return;
  }

  const rounds = shuffle(NEGOTIATION_ROUNDS).slice(0, 3);
  let correct = 0, mistakes = 0, forgiven = false;

  const intro = () => showModal({
    title: `${cr.name} — a wild Kindred`,
    sub: cr.blurb,
    body: `There is no trapping a Kindred. They join the travellers who <b>listen</b>.<br>` +
          `Win its trust across three exchanges. ` +
          (state.upgrades.suit ? `<i>Your tailored suit buys you one forgiven mistake.</i>` : ``),
    choices: [
      { label: 'Begin the conversation', cb: () => round(0) },
      { label: 'Walk away for now', cb: () => {} }
    ],
    closable: true
  });

  const round = (i) => {
    if (i >= rounds.length) { finish(); return; }
    const r = rounds[i];
    const opts = shuffle(r.options);
    showModal({
      title: `Exchange ${i + 1} of ${rounds.length}`,
      sub: `Trust so far: ${'❤️'.repeat(correct)}${'\u{1F494}'.repeat(i - correct)}${'\u{1F90D}'.repeat(rounds.length - i)} (win at least 2 of 3)`,
      body: `<i>${r.prompt(cr.name)}</i>`,
      choices: opts.map(o => ({
        label: o.text,
        cb: () => feedback(i, o)
      }))
    });
  };

  const feedback = (i, o) => {
    if (o.good) {
      correct++;
      if (o.note) addNote(o.note, o.teach);
    } else {
      if (state.upgrades.suit && !forgiven) { forgiven = true; }
      else mistakes++;
    }
    const forgivenNow = !o.good && forgiven && mistakes === 0;
    showModal({
      title: o.good ? '✨ It leans closer…' : (forgivenNow ? '\u{1F454} Saved by the suit' : '\u{1F4A8} It bristles…'),
      sub: o.good ? 'Trust grows.' : (forgivenNow ? 'Your composed presence smooths over the fumble. (One-time save)' : 'Trust wavers.'),
      body: `<div class="teach">${o.teach}</div>`,
      choices: [{ label: 'Continue', cb: () => round(i + 1) }]
    });
  };

  const finish = () => {
    if (correct >= 2) {
      state.befriended[cr.id] = true;
      state.party.push(cr.id);
      save();
      entities = entities.filter(x => x !== ent);
      const perfect = correct === rounds.length;
      showModal({
        title: `\u{1F31F} ${cr.name} joins you!`,
        sub: perfect ? 'A flawless negotiation. It trusts you completely.' : 'It nods slowly, and pads to your side.',
        body: `${cr.name} will now <b>gather ${COUNTRIES[state.country].goods.name}</b> while you travel ` +
              `(+${cr.gather} every few seconds, anywhere in the world).<br><br>` +
              `<i>“You didn’t capture me. You understood me. There’s a difference.”</i>` +
              (perfect ? `<br><br>\u{1F381} Perfect rapport bonus: <b>${fmt(30)}</b>` : ''),
        choices: [{ label: 'Welcome aboard', cb: () => { if (perfect) { state.money += 30; save(); updateHUD(); } checkWin(); } }]
      });
      updateHUD();
    } else {
      showModal({
        title: `${cr.name} drifts away…`,
        sub: 'Not this time.',
        body: `It wasn’t convinced — but Kindred hold no grudges. Reflect on the field notes in your journal ` +
              `(<b>J</b>) and try again whenever you like.`,
        choices: [{ label: 'I’ll be back', cb: () => {} }]
      });
    }
  };

  intro();
}

function checkWin() {
  if (state.won) return;
  if (CREATURES.every(c => state.befriended[c.id])) {
    state.won = true;
    save();
    setTimeout(() => showModal({
      title: '\u{1F30D} ATLAS MASTER',
      sub: 'All twelve Kindred walk beside you.',
      body: `You befriended every Kindred on four continents — not with traps, but with ` +
            `<b>listening, framing and nerve</b>.<br><br>Along the way you picked up ${state.notes.length} field notes: ` +
            `real techniques of negotiation, charisma and behavioural science. They work on humans too. ` +
            `<br><br><i>Use them kindly.</i>`,
      choices: [{ label: 'Keep travelling', cb: () => {} }],
      closable: true
    }), 400);
  }
}

/* ---------------- Cultural fluency ---------------- */

function startCulture() {
  const cid = state.country;
  const c = COUNTRIES[cid];
  const pool = CULTURE_SCENARIOS[cid];
  const fresh = pool.filter(s => !state.doneScenarios[s.id]);
  const scenario = (fresh.length ? fresh : pool)[Math.floor(Math.random() * (fresh.length ? fresh.length : pool.length))];
  const repeat = !fresh.length;

  showModal({
    title: `${c.flag} ${c.localName}`,
    sub: repeat ? 'A refresher, traveller?' : 'A situation comes up…',
    body: `<i>${scenario.q}</i>`,
    choices: shuffle(scenario.options).map(o => ({
      label: o.text,
      cb: () => {
        let gain, title, subTitle;
        if (o.good) {
          gain = repeat ? 3 : 12;
          title = '\u{1F91D} Smoothly done';
          subTitle = `Cultural fluency +${gain}%`;
          if (!repeat) { state.money += 10; }
        } else {
          gain = repeat ? 1 : 3;
          title = '\u{1F605} A little rough…';
          subTitle = `You still learned something. Fluency +${gain}%`;
        }
        state.fluency[cid] = Math.min(100, state.fluency[cid] + gain);
        state.doneScenarios[scenario.id] = true;
        const goodWhy = scenario.options.find(x => x.good).why;
        addCultureNote(cid, scenario, goodWhy);
        save(); updateHUD();
        showModal({
          title, sub: subTitle + (o.good && !repeat ? ` · tip ${fmt(10)}` : ''),
          body: `<div class="teach">${o.why}</div>` +
                (o.good ? '' : `<div class="teach alt"><b>The local way:</b> ${goodWhy}</div>`),
          choices: [{ label: 'Noted', cb: () => {} }]
        });
      }
    })),
    closable: true
  });
}

/* ---------------- Market haggle (selling goods) ---------------- */

function goodsTotal() {
  return Object.values(state.goods).reduce((a, b) => a + b, 0);
}

function goodsBaseValue() {
  const here = state.country;
  let base = 0;
  for (const [origin, qty] of Object.entries(state.goods)) {
    if (!qty) continue;
    const v = COUNTRIES[origin].goods.value;
    base += qty * v * (origin === here ? 1 : 1.6);   // arbitrage: foreign goods are exotic
  }
  base *= 1 + state.fluency[here] / 200;             // locals trust the culturally fluent
  if (state.upgrades.ledger) base *= 1.25;
  return base;
}

function startHaggle() {
  const c = COUNTRIES[state.country];
  if (goodsTotal() === 0) {
    showModal({
      title: c.merchantName,
      sub: 'Nothing to sell — yet.',
      body: `“Empty-handed? Befriend some <b>Kindred</b> — they gather goods for you as time passes. ` +
            `And a tip between traders: goods sell for <b>1.6× more far from home</b>. ` +
            `Distance creates value, friend.”`,
      choices: [{ label: 'Good to know', cb: () => { addNote('arbitrage', SUTHERLAND_NOTES.arbitrage); } }],
      closable: true
    });
    return;
  }

  const base = goodsBaseValue();
  let mult = 1.0;
  const hasForeign = Object.entries(state.goods).some(([o, q]) => q > 0 && o !== state.country);

  const inventoryHTML = Object.entries(state.goods)
    .filter(([, q]) => q > 0)
    .map(([o, q]) => `${COUNTRIES[o].goods.emoji} ${q}× ${COUNTRIES[o].goods.name}` +
                     (o !== state.country ? ' <b class="exotic">(exotic here! 1.6×)</b>' : ''))
    .join('<br>');

  const stepAnchor = () => showModal({
    title: c.merchantName,
    sub: `Your goods on the table:`,
    body: inventoryHTML + `<br><br><i>${HAGGLE.anchor.prompt(c.merchantName.split(' (')[0])}</i>`,
    choices: HAGGLE.anchor.options.map(o => ({
      label: o.text,
      cb: () => {
        let title, subT;
        if (o.id === 'high') {
          const credible = state.upgrades.story || state.fluency[state.country] >= 30;
          if (credible) {
            mult += 0.20;
            title = '\u{1F3AF} The anchor holds';
            subT = state.upgrades.story
              ? 'Your provenance story cards make the price feel inevitable. +20%'
              : 'Your local fluency makes the bold price credible. +20%';
            addNote('anchor', HAGGLE.anchor.options[0].teach + ' Pair a high anchor with a credible story and it holds.');
            if (state.upgrades.story) addNote('frame', SUTHERLAND_NOTES.frame);
          } else {
            mult += 0.05;
            title = '\u{1F928} The merchant scoffs';
            subT = 'A bold anchor with no story behind it wobbles. +5% only. (Fluency 30%+ or Story Cards make high anchors stick.)';
            addNote('anchor', HAGGLE.anchor.options[0].teach);
          }
        } else if (o.id === 'fair') {
          title = '\u{1F44C} Reasonable'; subT = 'A fair opener. Nothing gained, nothing risked.';
          addNote('anchor', HAGGLE.anchor.options[0].teach);
        } else {
          mult -= 0.10;
          title = '\u{1F4C9} Too easy'; subT = 'They accept instantly — always a bad sign. −10%';
          addNote('anchor', HAGGLE.anchor.options[0].teach);
        }
        showModal({ title, sub: subT, body: `<div class="teach">${o.teach}</div>`,
          choices: [{ label: 'Continue', cb: stepCounter }] });
      }
    }))
  });

  const stepCounter = () => {
    const counterOffer = fmt(base * (mult - 0.15));
    showModal({
      title: c.merchantName,
      body: `<i>${HAGGLE.counter.prompt(c.merchantName.split(' (')[0], counterOffer)}</i>`,
      choices: HAGGLE.counter.options.map(o => ({
        label: o.text,
        cb: () => {
          let title, subT;
          if (o.id === 'calibrated') {
            title = '\u{1F9E0} They blink first';
            subT = '“Well… I suppose I could stretch a little.” Your price stands.';
            addNote('calibrated', NEGOTIATION_ROUNDS.find(r => r.id === 'calibrated').options[0].teach);
          } else if (o.id === 'split') {
            mult -= 0.08;
            title = '✂️ Split — and lost';
            subT = 'Meeting in the middle of THEIR range. −8%';
            addNote('split', o.teach);
          } else {
            mult -= 0.15;
            title = '\u{1F91D} Deal — their deal';
            subT = 'You took the counter. −15%';
          }
          showModal({ title, sub: subT, body: `<div class="teach">${o.teach}</div>`,
            choices: [{ label: 'Continue', cb: stepClose }] });
        }
      }))
    });
  };

  const stepClose = () => showModal({
    title: c.merchantName,
    body: `<i>${HAGGLE.close.prompt(c.merchantName.split(' (')[0])}</i>`,
    choices: HAGGLE.close.options.map(o => ({
      label: o.text,
      cb: () => {
        let title, subT;
        if (o.id === 'silence') {
          mult += 0.07;
          title = '\u{1F92B} The silence pays';
          subT = '“…Oh, FINE. A little extra for your trouble.” +7%';
          addNote('silence', o.teach);
        } else if (o.id === 'eager') {
          title = '\u{1F604} Enthusiastic'; subT = 'Deal closed — but they’ve noted your eagerness for next time.';
        } else {
          mult -= 0.05;
          title = '\u{1F9E2} You got the hat…'; subT = '…and a cooler handshake. −5%';
        }
        showModal({ title, sub: subT, body: `<div class="teach">${o.teach}</div>`,
          choices: [{ label: 'Shake on it', cb: () => settle() }] });
      }
    }))
  });

  const settle = () => {
    const final = Math.max(5, Math.round(base * mult));
    state.money += final;
    state.goods = { london: 0, usa: 0, japan: 0, india: 0 };
    save(); updateHUD();
    if (hasForeign) addNote('arbitrage', SUTHERLAND_NOTES.arbitrage);
    showModal({
      title: `\u{1F4B0} Sold for ${fmt(final)}`,
      sub: `Base value ${fmt(base)} × negotiation ${(mult * 100).toFixed(0)}%`,
      body: `Fluency here (+${Math.round(state.fluency[state.country] / 2)}%)` +
            (state.upgrades.ledger ? ', your Ledger (+25%)' : '') +
            (hasForeign ? ', and exotic goods (1.6×)' : '') +
            ` all fed into the base price. The rest was <b>pure negotiation</b>.`,
      choices: [{ label: 'Excellent', cb: () => {} }],
      closable: true
    });
  };

  stepAnchor();
}

/* ---------------- Shop ---------------- */

function openShop() {
  const rows = UPGRADES.map((u, i) => {
    const owned = state.upgrades[u.id];
    return {
      label: `${u.emoji} ${u.name} — ${owned ? 'OWNED' : fmt(u.price)}<br><small>${u.desc}</small>`,
      cb: () => {
        if (owned) { toast('Already owned.'); openShop(); return; }
        if (state.money < u.price) { toast(`Not enough coin — need ${fmt(u.price)}.`); openShop(); return; }
        state.money -= u.price;
        state.upgrades[u.id] = true;
        save(); updateHUD();
        if (u.note) addNote(u.note, SUTHERLAND_NOTES[u.note]);
        showModal({
          title: `${u.emoji} ${u.name} acquired`,
          body: `<div class="teach">${u.note ? SUTHERLAND_NOTES[u.note] : 'Your Kindred purr approvingly. Gathering speeds up.'}</div>`,
          choices: [{ label: 'Back to the rack', cb: openShop }, { label: 'Done shopping', cb: () => {} }]
        });
      }
    };
  });
  rows.push({ label: 'Leave the shop', cb: () => {} });
  showModal({
    title: '\u{1F3EA} The Outfitter',
    sub: `“Everything here is overpriced — that’s HOW it works, friend.” · You carry ${fmt(state.money)}`,
    choices: rows,
    closable: true
  });
}

/* ---------------- Travel map ---------------- */

function openTravelMap() {
  const cards = Object.values(COUNTRIES).map(c => {
    const here = c.id === state.country;
    const flu = state.fluency[c.id];
    const kin = CREATURES.filter(x => x.country === c.id);
    const got = kin.filter(x => state.befriended[x.id]).length;
    const goodsHint = Object.entries(state.goods).some(([o, q]) => q > 0 && o !== c.id)
      ? ' · your foreign goods sell 1.6× here' : '';
    return {
      label: `${c.flag} <b>${c.name}</b> ${here ? '\u{1F4CD} (you are here)' : `— fly for ${fmt(TRAVEL_COST)}`}` +
             `<br><small>${c.tagline} · fluency ${flu}% · Kindred ${got}/${kin.length}${here ? '' : goodsHint}</small>`,
      cb: () => {
        if (here) { toast('You are already here.'); return; }
        if (state.money < TRAVEL_COST) { toast(`A ticket costs ${fmt(TRAVEL_COST)} — sell some goods first.`); return; }
        state.money -= TRAVEL_COST;
        save();
        enterCountry(c.id);
        player.x = W / 2; player.y = H / 2 + 60;
      }
    };
  });
  cards.push({ label: 'Stay put', cb: () => {} });
  showModal({
    title: '✈️ World Atlas — pick a destination',
    sub: `One click and you’re there. Tickets ${fmt(TRAVEL_COST)}. (Open anytime with M)`,
    choices: cards,
    closable: true
  });
}

/* ---------------- Journal ---------------- */

function openJournal() {
  const groups = {};
  for (const n of state.notes) {
    (groups[n.source] = groups[n.source] || []).push(n);
  }
  let body;
  if (!state.notes.length) {
    body = 'Empty — for now. Every negotiation, haggle and cultural moment teaches you something real. It all lands here.';
  } else {
    body = Object.entries(groups).map(([src, notes]) =>
      `<div class="journal-src">${src}</div>` +
      notes.map(n => `<details><summary>${n.title}</summary><div class="teach">${n.text}</div></details>`).join('')
    ).join('');
  }
  showModal({
    title: `\u{1F4D3} Field Notes (${state.notes.length})`,
    sub: 'Real techniques you’ve picked up along the way — they work outside the game too.',
    body: `<div class="journal">${body}</div>`,
    choices: [{ label: 'Close journal', cb: () => {} }],
    closable: true
  });
}

/* ---------------- Help / intro ---------------- */

function openHelp() {
  showModal({
    title: '\u{1F9ED} How to travel well',
    body:
      `<b>Move</b> — WASD or arrow keys<br>` +
      `<b>Talk / interact</b> — E (near a creature, merchant or local)<br>` +
      `<b>World map</b> — M, or walk into the ✈️ airport<br>` +
      `<b>Journal</b> — J · <b>Help</b> — H<br><br>` +
      `<b>The loop:</b> befriend Kindred by <i>negotiating</i> (they gather goods) → ` +
      `learn local customs from the local (fluency = better prices & shy Kindred) → ` +
      `sell goods to merchants (haggling is a mini-game) → fly somewhere new — ` +
      `<b>foreign goods sell for 1.6×</b>.`,
    choices: [{ label: 'Got it', cb: () => {} }],
    closable: true
  });
}

function showIntro() {
  showModal({
    title: '\u{1F30D} KINDRED ATLAS',
    sub: 'A trader’s journey across four cultures',
    body:
      `Wild spirit-creatures called <b>Kindred</b> live in London, the USA, Japan and India. ` +
      `They cannot be caught, bought or trapped — only <b>persuaded</b>.<br><br>` +
      `Befriend them with real negotiation technique. Trade with real haggling craft. ` +
      `Learn each culture’s unwritten rules. Everything you learn in here… works out there.<br><br>` +
      `<i>You start in London with ${fmt(150)} in your pocket.</i>`,
    choices: [{ label: 'Begin in London', cb: () => { state.intro = true; save(); openHelp(); } }]
  });
}

/* ---------------- Gathering tick ---------------- */

setInterval(() => {
  if (!state.party.length) return;
  let gained = 0;
  for (const id of state.party) {
    const cr = CREATURES.find(c => c.id === id);
    if (cr) gained += cr.gather;
  }
  if (gained > 0) {
    state.goods[state.country] += gained;
    save(); updateHUD();
  }
}, GATHER_INTERVAL_MS / ((state.upgrades && state.upgrades.teaset) ? 1.25 : 1));

/* ---------------- HUD ---------------- */

function updateHUD() {
  const c = COUNTRIES[state.country];
  hudMoney.textContent = fmt(state.money);
  hudGoods.textContent = '\u{1F4E6} ' + goodsTotal();
  hudParty.textContent = '\u{1F43E} ' + state.party.length + '/12';
  hudFluency.textContent = `\u{1F5E3}️ ${state.fluency[state.country]}%`;
  hudCountry.textContent = `${c.flag} ${c.name}`;
}

/* ---------------- Update & render ---------------- */

let t = 0;

function update() {
  if (!modalOpen) {
    let dx = 0, dy = 0;
    if (keys['w'] || keys['arrowup']) dy -= 1;
    if (keys['s'] || keys['arrowdown']) dy += 1;
    if (keys['a'] || keys['arrowleft']) dx -= 1;
    if (keys['d'] || keys['arrowright']) dx += 1;
    if (dx || dy) {
      const len = Math.hypot(dx, dy);
      player.x += (dx / len) * player.speed;
      player.y += (dy / len) * player.speed;
      player.x = Math.max(20, Math.min(W - 20, player.x));
      player.y = Math.max(90, Math.min(H - 20, player.y));
    }
  }

  // creatures wander
  for (const e of entities) {
    if (e.kind !== 'creature') continue;
    e.wanderT -= 1;
    if (e.wanderT <= 0) {
      e.wanderT = rnd(60, 180);
      const a = rnd(0, Math.PI * 2);
      e.vx = Math.cos(a) * 0.5; e.vy = Math.sin(a) * 0.5;
    }
    // drift toward player a little if close (curious creatures)
    const d = Math.hypot(player.x - e.x, player.y - e.y);
    if (d < 120 && d > 50) { e.vx += (player.x - e.x) / d * 0.02; e.vy += (player.y - e.y) / d * 0.02; }
    e.x += e.vx; e.y += e.vy;
    e.x = Math.max(40, Math.min(W - 40, e.x));
    e.y = Math.max(120, Math.min(H - 160, e.y));
  }

  // interaction prompt
  if (!modalOpen) {
    if (inAirport()) {
      promptEl.textContent = '✈️ Press E to open the World Atlas';
      promptEl.classList.add('show');
    } else {
      const e = nearestInteractable();
      if (e) {
        const label = e.kind === 'creature' ? `Negotiate with ${e.ref.name}` :
                      e.kind === 'merchant' ? `Trade with ${e.name}` :
                      e.kind === 'local' ? `Chat with ${e.name} (learn the local ways)` :
                      `Browse ${e.name}`;
        promptEl.textContent = `E — ${label}`;
        promptEl.classList.add('show');
      } else promptEl.classList.remove('show');
    }
  } else promptEl.classList.remove('show');
}

/* ---------- drawing ---------- */

function draw() {
  const c = COUNTRIES[state.country];
  t += 0.02;

  // sky band + ground
  ctx.fillStyle = c.sky; ctx.fillRect(0, 0, W, 90);
  ctx.fillStyle = c.ground; ctx.fillRect(0, 90, W, H - 90);

  // path
  ctx.fillStyle = c.path;
  ctx.fillRect(0, H - 220, W, 60);
  ctx.fillRect(W / 2 - 30, 90, 60, H - 90);

  drawLandmark(c.id);
  drawAirport();

  // entities sorted by y for pseudo-depth
  const drawables = entities.slice().sort((a, b) => a.y - b.y);
  let playerDrawn = false;
  for (const e of drawables) {
    if (!playerDrawn && player.y < e.y) { drawPlayer(); playerDrawn = true; }
    if (e.kind === 'creature') drawCreature(e);
    else drawNPC(e);
  }
  if (!playerDrawn) drawPlayer();

  // country name watermark (bottom-left, clear of the landmark art)
  ctx.fillStyle = 'rgba(255,255,255,0.85)';
  ctx.font = 'bold 18px Georgia, serif';
  ctx.textAlign = 'left';
  ctx.fillText(`${c.name} — ${c.tagline}`, 16, H - 14);
}

function drawLandmark(cid) {
  ctx.save();
  ctx.translate(W / 2, 90);
  if (cid === 'london') {
    // clock tower
    ctx.fillStyle = '#7a6a52'; ctx.fillRect(-260, -70, 34, 70);
    ctx.fillStyle = '#e8dcc0'; ctx.beginPath(); ctx.arc(-243, -48, 11, 0, 7); ctx.fill();
    ctx.strokeStyle = '#333'; ctx.beginPath(); ctx.moveTo(-243, -48); ctx.lineTo(-243, -56); ctx.moveTo(-243, -48); ctx.lineTo(-237, -46); ctx.stroke();
    ctx.fillStyle = '#5a4a38'; ctx.beginPath(); ctx.moveTo(-260, -70); ctx.lineTo(-243, -86); ctx.lineTo(-226, -70); ctx.fill();
    // phone box
    ctx.fillStyle = '#b03a3a'; ctx.fillRect(210, -44, 26, 44);
    ctx.fillStyle = '#e8dcc0'; ctx.fillRect(214, -38, 18, 24);
  } else if (cid === 'usa') {
    // skyline
    ctx.fillStyle = '#5a6a7a';
    ctx.fillRect(-290, -55, 30, 55); ctx.fillRect(-250, -75, 26, 75); ctx.fillRect(-216, -45, 34, 45);
    // neon diner sign
    ctx.fillStyle = '#e05a8a'; ctx.fillRect(200, -50, 80, 30);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px monospace'; ctx.textAlign = 'center';
    ctx.fillText('DINER', 240, -30);
  } else if (cid === 'japan') {
    // torii-style gate (generic shrine gate)
    ctx.strokeStyle = '#c4485a'; ctx.lineWidth = 10;
    ctx.beginPath(); ctx.moveTo(-270, 0); ctx.lineTo(-270, -70); ctx.moveTo(-200, 0); ctx.lineTo(-200, -70); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-290, -70); ctx.lineTo(-180, -70); ctx.moveTo(-280, -50); ctx.lineTo(-190, -50); ctx.stroke();
    // blossom tree
    ctx.fillStyle = '#8a6a4a'; ctx.fillRect(226, -40, 10, 40);
    ctx.fillStyle = '#e8b4c8';
    ctx.beginPath(); ctx.arc(231, -48, 24, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(212, -38, 15, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(250, -38, 15, 0, 7); ctx.fill();
  } else if (cid === 'india') {
    // domed pavilion
    ctx.fillStyle = '#e8dcc8'; ctx.fillRect(-280, -45, 90, 45);
    ctx.beginPath(); ctx.arc(-235, -45, 32, Math.PI, 0); ctx.fill();
    ctx.fillStyle = '#d4691e'; ctx.fillRect(-238, -82, 6, 10);
    // market awning
    ctx.fillStyle = '#d4548a'; ctx.fillRect(200, -35, 80, 12);
    ctx.fillStyle = '#e8c34a';
    for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.arc(210 + i * 20, -23, 10, 0, Math.PI); ctx.fill(); }
  }
  ctx.restore();
}

function drawAirport() {
  const a = airportZone;
  ctx.fillStyle = 'rgba(255,255,255,0.16)';
  ctx.fillRect(a.x, a.y, a.w, a.h);
  ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.setLineDash([6, 5]);
  ctx.strokeRect(a.x, a.y, a.w, a.h); ctx.setLineDash([]);
  ctx.fillStyle = '#fff'; ctx.font = '22px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('✈️', a.x + a.w / 2, a.y + 38);
  ctx.font = 'bold 12px sans-serif';
  ctx.fillText('AIRPORT', a.x + a.w / 2, a.y + 60);
  ctx.font = '11px sans-serif';
  ctx.fillText('(or press M)', a.x + a.w / 2, a.y + 76);
}

function drawPlayer() {
  const { x, y } = player;
  ctx.fillStyle = 'rgba(0,0,0,0.25)';
  ctx.beginPath(); ctx.ellipse(x, y + 12, 12, 5, 0, 0, 7); ctx.fill();
  ctx.fillStyle = '#e8c9a0';
  ctx.beginPath(); ctx.arc(x, y - 6, 9, 0, 7); ctx.fill();
  ctx.fillStyle = '#3f6b5e';
  ctx.fillRect(x - 9, y - 1, 18, 14);
  ctx.fillStyle = '#7a5230';           // satchel
  ctx.fillRect(x + 6, y + 2, 7, 9);
  ctx.fillStyle = '#4a3826';           // explorer hat
  ctx.beginPath(); ctx.ellipse(x, y - 12, 12, 4, 0, 0, 7); ctx.fill();
  ctx.fillRect(x - 7, y - 20, 14, 8);
}

function drawNPC(e) {
  const bob = Math.sin(t * 2 + e.x) * 1.5;
  const y = e.y + bob;
  ctx.fillStyle = 'rgba(0,0,0,0.25)';
  ctx.beginPath(); ctx.ellipse(e.x, e.y + 12, 12, 5, 0, 0, 7); ctx.fill();
  const col = e.kind === 'merchant' ? '#8a5a2b' : e.kind === 'outfitter' ? '#5a4a8a' : COUNTRIES[state.country].accent;
  ctx.fillStyle = '#e8c9a0'; ctx.beginPath(); ctx.arc(e.x, y - 6, 9, 0, 7); ctx.fill();
  ctx.fillStyle = col; ctx.fillRect(e.x - 9, y - 1, 18, 14);
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.font = 'bold 11px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(e.name, e.x, y - 24);
}

function drawCreature(e) {
  const cr = e.ref;
  const bob = Math.sin(t * 3 + e.x) * 3;
  const x = e.x, y = e.y + bob;
  const locked = cr.minFluency > state.fluency[state.country];

  ctx.save();
  if (locked) ctx.globalAlpha = 0.45;
  ctx.fillStyle = 'rgba(0,0,0,0.2)';
  ctx.beginPath(); ctx.ellipse(x, e.y + 14, 13, 5, 0, 0, 7); ctx.fill();

  ctx.fillStyle = cr.color;
  switch (cr.art) {
    case 'wisp':
      ctx.beginPath(); ctx.arc(x, y, 12, 0, 7); ctx.fill();
      ctx.globalAlpha *= 0.5;
      ctx.beginPath(); ctx.arc(x - 10, y + 6, 7, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.arc(x - 18, y + 10, 4, 0, 7); ctx.fill();
      break;
    case 'tea':
      ctx.beginPath(); ctx.arc(x, y, 11, 0, Math.PI); ctx.fill();
      ctx.fillRect(x - 11, y - 4, 22, 5);
      ctx.strokeStyle = cr.color2; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(x + 13, y + 2, 5, -1.2, 1.2); ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.6)';
      ctx.beginPath(); ctx.moveTo(x - 3, y - 8); ctx.quadraticCurveTo(x, y - 14, x + 3, y - 9); ctx.stroke();
      break;
    case 'chimney':
      ctx.fillRect(x - 8, y - 10, 16, 22);
      ctx.fillStyle = cr.color2; ctx.fillRect(x - 11, y - 14, 22, 6);
      ctx.fillStyle = 'rgba(220,220,220,0.7)';
      ctx.beginPath(); ctx.arc(x + 2, y - 20 - bob, 4 + Math.sin(t * 4) * 1.5, 0, 7); ctx.fill();
      break;
    case 'note':
      ctx.beginPath(); ctx.ellipse(x - 3, y + 6, 8, 6, -0.4, 0, 7); ctx.fill();
      ctx.fillRect(x + 3, y - 14, 3.5, 20);
      ctx.beginPath(); ctx.moveTo(x + 3, y - 14); ctx.quadraticCurveTo(x + 15, y - 12, x + 13, y - 4);
      ctx.quadraticCurveTo(x + 10, y - 10, x + 6.5, y - 9); ctx.fill();
      break;
    case 'bison':
      ctx.beginPath(); ctx.ellipse(x, y, 14, 10, 0, 0, 7); ctx.fill();
      ctx.fillStyle = cr.color2;
      ctx.beginPath(); ctx.arc(x + 10, y - 4, 7, 0, 7); ctx.fill();
      ctx.strokeStyle = '#e8dcc0'; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.arc(x + 14, y - 10, 4, Math.PI * 0.5, Math.PI * 1.5); ctx.stroke();
      break;
    case 'star': {
      ctx.beginPath();
      for (let i = 0; i < 10; i++) {
        const ang = -Math.PI / 2 + i * Math.PI / 5;
        const r = i % 2 === 0 ? 14 : 6;
        ctx[i === 0 ? 'moveTo' : 'lineTo'](x + Math.cos(ang) * r, y + Math.sin(ang) * r);
      }
      ctx.closePath(); ctx.fill();
      break;
    }
    case 'lantern':
      ctx.fillStyle = `rgba(232,160,74,${0.25 + Math.sin(t * 3) * 0.1})`;
      ctx.beginPath(); ctx.arc(x, y, 18, 0, 7); ctx.fill();
      ctx.fillStyle = cr.color;
      ctx.beginPath(); ctx.ellipse(x, y, 10, 13, 0, 0, 7); ctx.fill();
      ctx.strokeStyle = cr.color2; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x - 9, y - 5); ctx.lineTo(x + 9, y - 5);
      ctx.moveTo(x - 10, y); ctx.lineTo(x + 10, y);
      ctx.moveTo(x - 9, y + 5); ctx.lineTo(x + 9, y + 5); ctx.stroke();
      ctx.fillStyle = cr.color2; ctx.fillRect(x - 4, y - 16, 8, 4);
      break;
    case 'fox':
      ctx.beginPath(); ctx.arc(x, y, 11, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x - 9, y - 6); ctx.lineTo(x - 6, y - 16); ctx.lineTo(x - 1, y - 8); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 9, y - 6); ctx.lineTo(x + 6, y - 16); ctx.lineTo(x + 1, y - 8); ctx.fill();
      ctx.fillStyle = cr.color2;
      ctx.beginPath(); ctx.ellipse(x + 13, y + 5, 8, 4, 0.6, 0, 7); ctx.fill();
      ctx.fillStyle = '#4a3040';
      ctx.beginPath(); ctx.arc(x - 4, y - 1, 1.5, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.arc(x + 4, y - 1, 1.5, 0, 7); ctx.fill();
      break;
    case 'mochi':
      ctx.beginPath(); ctx.ellipse(x, y + 3, 13, 9, 0, 0, 7); ctx.fill();
      ctx.fillStyle = cr.color2;
      ctx.beginPath(); ctx.ellipse(x, y - 4, 7, 4, 0, 0, 7); ctx.fill();
      ctx.fillStyle = '#4a3040';
      ctx.beginPath(); ctx.arc(x - 4, y + 2, 1.5, 0, 7); ctx.fill();
      ctx.beginPath(); ctx.arc(x + 4, y + 2, 1.5, 0, 7); ctx.fill();
      break;
    case 'monsoon':
      ctx.beginPath(); ctx.arc(x - 6, y, 8, 0, 7); ctx.arc(x + 4, y - 3, 9, 0, 7); ctx.arc(x + 10, y + 2, 6, 0, 7); ctx.fill();
      ctx.strokeStyle = cr.color2; ctx.lineWidth = 2;
      for (let i = -1; i <= 1; i++) {
        const off = (t * 30 + i * 20) % 12;
        ctx.beginPath(); ctx.moveTo(x + i * 7, y + 8 + off); ctx.lineTo(x + i * 7 - 2, y + 13 + off); ctx.stroke();
      }
      break;
    case 'peacock':
      ctx.strokeStyle = cr.color; ctx.lineWidth = 3;
      for (let i = -2; i <= 2; i++) {
        ctx.beginPath(); ctx.moveTo(x, y + 4);
        ctx.lineTo(x + i * 8, y - 14 + Math.abs(i) * 3); ctx.stroke();
        ctx.fillStyle = i % 2 ? '#e8c34a' : cr.color2;
        ctx.beginPath(); ctx.arc(x + i * 8, y - 14 + Math.abs(i) * 3, 3.5, 0, 7); ctx.fill();
      }
      ctx.fillStyle = cr.color;
      ctx.beginPath(); ctx.ellipse(x, y + 7, 8, 6, 0, 0, 7); ctx.fill();
      break;
    case 'pattern':
      for (let i = 0; i < 6; i++) {
        const ang = t + i * Math.PI / 3;
        ctx.fillStyle = i % 2 ? cr.color : cr.color2;
        ctx.beginPath(); ctx.arc(x + Math.cos(ang) * 10, y + Math.sin(ang) * 10, 4, 0, 7); ctx.fill();
      }
      ctx.fillStyle = '#e8c34a';
      ctx.beginPath(); ctx.arc(x, y, 4.5, 0, 7); ctx.fill();
      break;
    default:
      ctx.beginPath(); ctx.arc(x, y, 12, 0, 7); ctx.fill();
  }

  ctx.fillStyle = locked ? 'rgba(255,255,255,0.7)' : '#fff';
  ctx.font = 'bold 11px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(locked ? `${cr.name} \u{1F512} fluency ${cr.minFluency}%` : cr.name, x, y - 26);
  ctx.restore();
}

/* ---------------- Main loop ---------------- */

function frame() {
  update();
  draw();
  requestAnimationFrame(frame);
}

enterCountry(state.country);
updateHUD();
if (!state.intro) showIntro();
frame();
