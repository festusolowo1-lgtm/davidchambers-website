/* DAVID CHAMBERS — Shared JS v3.0 */

// ── NAVBAR ────────────────────────────────────────────────────────────
var navbar = document.querySelector('.navbar');
var hamburger = document.querySelector('.hamburger');
var mobileMenu = document.querySelector('.mobile-menu');

hamburger && hamburger.addEventListener('click', function() {
  mobileMenu && mobileMenu.classList.toggle('open');
});
document.querySelectorAll('.mobile-menu a').forEach(function(a) {
  a.addEventListener('click', function() { mobileMenu && mobileMenu.classList.remove('open'); });
});

// Active link
var path = window.location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(function(a) {
  var href = a.getAttribute('href') || '';
  if (href === path || href.endsWith('/' + path)) a.classList.add('active');
});

// ── SCROLL REVEAL ─────────────────────────────────────────────────────
var revealObs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) {
    if (e.isIntersecting) { e.target.classList.add('visible'); revealObs.unobserve(e.target); }
  });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(function(el) { revealObs.observe(el); });

// ── COUNTER ANIMATION ─────────────────────────────────────────────────
var counterObs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) {
    if (e.isIntersecting) { animateCounter(e.target); counterObs.unobserve(e.target); }
  });
}, { threshold: 0.5 });
function animateCounter(el) {
  var target = parseInt(el.dataset.target, 10);
  if (isNaN(target)) return;
  var step = Math.ceil(target / 60), current = 0;
  var tm = setInterval(function() {
    current = Math.min(current + step, target);
    el.textContent = current + (el.dataset.suffix || '+');
    if (current >= target) clearInterval(tm);
  }, 25);
}
document.querySelectorAll('[data-target]').forEach(function(el) {
  if (!isNaN(parseInt(el.dataset.target, 10))) counterObs.observe(el);
});

// ── TOAST ─────────────────────────────────────────────────────────────
function showToast(msg, type) {
  var t = document.getElementById('app-toast');
  if (!t) { t = document.createElement('div'); t.id = 'app-toast'; t.className = 'toast'; document.body.appendChild(t); }
  t.style.borderLeftColor = type === 'err' ? '#b71c2a' : '#c9a84c';
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._tm);
  t._tm = setTimeout(function() { t.classList.remove('show'); }, 3500);
}

// ── CHATBOT ───────────────────────────────────────────────────────────
var RULES = [
  {t:/consult|book|appoint/i,         r:'Our <strong>free 15-min consultation</strong> is Mon–Fri, 9AM–5PM.<br>📅 <a href="pages/booking.html" style="color:var(--gold2);font-weight:600">Book online</a> or call <strong>08037098327</strong>.'},
  {t:/fee|cost|how much|price|naira/i, r:'Consultation: <strong>Free</strong> · Doc Review: from <strong>₦25k</strong> · Incorporation: from <strong>₦75k</strong> · Immigration: from <strong>₦50k</strong> · Family Law: from <strong>₦100k</strong> · Conveyancing: from <strong>₦150k</strong>'},
  {t:/property|land|convey|title/i,   r:'Our Property team handles title verification, Governor\'s Consent, conveyancing (from ₦150,000). Call <strong>08037098327</strong>.'},
  {t:/criminal|arrest|bail|efcc/i,    r:'⚠️ Time is critical. We handle bail, EFCC/ICPC, trial defense. Call <strong>immediately: 08037098327</strong>.'},
  {t:/family|divorce|custody/i,       r:'Family Law from <strong>₦100,000</strong>. Divorce, custody, inheritance. Call <strong>08037098327</strong>.'},
  {t:/company|incorporat|cac/i,       r:'Business incorporation from <strong>₦75,000</strong>. CAC registration, contracts. Call <strong>08037098327</strong>.'},
  {t:/immigrat|visa|cerpac/i,         r:'Immigration from <strong>₦50,000</strong>. CERPAC, work permits, residency. Call <strong>08037098327</strong>.'},
  {t:/hello|hi\b|hey\b|good/i,        r:'Good day! Welcome to <strong>DAVID CHAMBERS</strong> 👋 How can I assist you today?'},
  {t:/hour|open|when/i,               r:'We are open <strong>Monday–Friday, 9AM–5PM WAT</strong>. WhatsApp anytime: <strong>08037098327</strong>.'},
  {t:/location|address|abuja/i,       r:'Based in <strong>Abuja FCT, Nigeria</strong>. We serve clients nationwide via phone, WhatsApp and video.'},
  {t:/contact|whatsapp|phone|email/i, r:'📱 <a href="https://wa.me/2348037098327" style="color:var(--gold2)" target="_blank">WhatsApp: 08037098327</a><br>📧 davidchambers542@yahoo.com'},
  {t:/thank/i,                        r:'You\'re most welcome! 😊 First consultation is <strong>free</strong>. Call <strong>08037098327</strong>.'},
];

function addMsg(role, html) {
  var box = document.getElementById('chatbot-msgs');
  if (!box) return null;
  var d = document.createElement('div');
  d.className = 'chat-msg ' + role;
  d.innerHTML = html;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
  return d;
}
function sendChat() {
  var inp = document.getElementById('chatbot-input');
  var txt = (inp && inp.value || '').trim();
  if (!txt) return;
  addMsg('user', txt);
  inp.value = '';
  var dot = addMsg('bot typing', '<span></span><span></span><span></span>');
  setTimeout(function() {
    dot && dot.remove();
    var reply = '📱 <a href="https://wa.me/2348037098327" style="color:var(--gold2)" target="_blank">08037098327</a>';
    for (var i = 0; i < RULES.length; i++) { if (RULES[i].t.test(txt)) { reply = RULES[i].r; break; } }
    addMsg('bot', reply);
  }, 600);
}
var fab = document.querySelector('.chatbot-fab');
var panel = document.querySelector('.chatbot-panel');
fab && fab.addEventListener('click', function() {
  panel && panel.classList.toggle('open');
  fab.innerHTML = (panel && panel.classList.contains('open'))
    ? '<i class="fas fa-times"></i>' : '<i class="fas fa-comments"></i>';
});
document.querySelector('.close-chatbot') && document.querySelector('.close-chatbot').addEventListener('click', function() {
  panel && panel.classList.remove('open');
  fab && (fab.innerHTML = '<i class="fas fa-comments"></i>');
});
document.getElementById('chatbot-send') && document.getElementById('chatbot-send').addEventListener('click', sendChat);
document.getElementById('chatbot-input') && document.getElementById('chatbot-input').addEventListener('keydown', function(e) { if (e.key === 'Enter') sendChat(); });
setTimeout(function() {
  addMsg('bot', 'Welcome to <strong>DAVID CHAMBERS</strong> 👋<br>Ask about our services, fees, or book a free consultation.');
}, 800);

// ── LOGO LOADER (runs on every page) ─────────────────────────────────
(function() {
  fetch('/api/public/settings')
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
      if (!data || !data.logo) return;
      document.querySelectorAll('.nav-logo-emblem').forEach(function(emblem) {
        var img = document.createElement('img');
        img.src = '/' + data.logo + '?v=' + Date.now();
        img.alt = 'David Chambers';
        img.className = 'nav-logo-img';
        img.style.cssText = 'height:46px;width:auto;display:block';
        img.onerror = function() { img.style.display = 'none'; };
        emblem.parentNode.replaceChild(img, emblem);
      });
    })
    .catch(function() {});
})();
