// ===== DEBUG: บอกให้รู้ว่าไฟล์นี้ถูกโหลดจริง และระบุเวอร์ชัน =====
console.log("[typing_game.js] v2025-08-23 loaded", new Date().toISOString());

// ===== เสียง =====
const TypingSound = new Audio("/static/sounds/Keyboard-02.wav");
const wrongSound = new Audio("/static/sounds/mixkit-cowbell-sharp-hit-1743.wav");

// ===== ค่าจาก template =====
const words = window.words;
const category = window.category;

// ภาษา: รองรับทั้งตัวพิมพ์ใหญ่/เล็ก + query + localStorage
const urlParams = new URLSearchParams(window.location.search);
const srcLang =
  window.SRC_LANG || window.srcLang ||
  urlParams.get('src') || localStorage.getItem('tt_srcLang') || 'en';
const destLang =
  window.DEST_LANG || window.destLang ||
  urlParams.get('dest') || localStorage.getItem('tt_destLang') || 'th';

// เวลาค้างแสดงคำแปลก่อนข้ามคำ (ms)
const HOLD_MS = parseInt(
  urlParams.get('hold') || localStorage.getItem('tt_hold_ms') || '500',
  10
);

// ===== สถานะเกม =====
let index = 0;
let userInput = "";
let totalScore = 0;         // จำนวน “คำ” ที่พิมพ์ถูก
let correctChars = 0;       // จำนวน “ตัวอักษร” ที่พิมพ์ถูก (ใช้คำนวณ WPM)
const maxWordsToPlay = words.length;  // server ตัดมาแล้วตาม max_words
const historyItems = [];

// จับเวลา (สต็อปวอช — ไม่จำกัดเวลา)
let startTime = null;       // performance.now() เมื่อเริ่มพิมพ์ครั้งแรก
let tickIntervalId = null;  // setInterval สำหรับอัปเดต HUD
let lastSentSeconds = 0;    // เก็บเวลาที่ “ส่งไปแล้ว” เพื่อคำนวณ delta

// ===== DOM =====
const currentWord = document.getElementById("current-word");
const translation = document.getElementById("translation");
const letterBoxes = document.getElementById("letter-boxes");
const inputBox = document.getElementById("hidden-input");
const historyPanel = document.getElementById('history-panel');
const historyList = document.getElementById('history-list');
const historyOpenBtn = document.getElementById('history-open');
const historyCloseBtn = document.getElementById('history-close');

// HUD แสดงเวลา+WPM+คะแนน (สร้างอัตโนมัติ)
const hud = document.createElement('div');
hud.id = 'hud';
hud.style.display = 'flex';
hud.style.justifyContent = 'center';
hud.style.gap = '16px';
hud.style.margin = '8px 0 12px';
hud.style.fontSize = '1rem';
const hudTime = document.createElement('span');
const hudWpm = document.createElement('span');
const hudScore = document.createElement('span');
hud.appendChild(hudTime);
hud.appendChild(hudWpm);
hud.appendChild(hudScore);
(currentWord?.parentElement || document.body).insertBefore(hud, currentWord.nextSibling);

let currentWordText = words[index];
// ===== Speech (Web Speech API) =====
const Speech = {
  voices: [],
  ready: false,
  langFallbackMap: {
    en: 'en-US',
    th: 'th-TH',
    ja: 'ja-JP',
    ko: 'ko-KR',
    zh: 'zh-CN',   // หรือ zh-TW ตามชุดคำของคุณ
    es: 'es-ES',
    fr: 'fr-FR',
    de: 'de-DE'
  },
  normalizeLang(code) {
    if (!code) return 'en-US';
    code = String(code).toLowerCase();
    // ถ้าได้ en-US อยู่แล้วก็คืนเลย
    if (code.includes('-')) return code;
    return this.langFallbackMap[code] || 'en-US';
  },
  loadVoices() {
    try {
      this.voices = window.speechSynthesis.getVoices() || [];
      this.ready = this.voices.length > 0;
    } catch {
      this.voices = [];
      this.ready = false;
    }
  },
  getVoiceFor(langCode) {
    const want = this.normalizeLang(langCode);
    if (!this.ready) this.loadVoices();

    // พยายาม match แบบ exact ก่อน
    let v = this.voices.find(v => v.lang && v.lang.toLowerCase() === want.toLowerCase());
    if (v) return v;

    // พยายาม match แบบ prefix (เช่น en-* )
    const prefix = want.split('-')[0];
    v = this.voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
    if (v) return v;

    // ไม่เจอ ก็คืน default (ปล่อยให้เบราว์เซอร์เลือก)
    return null;
  },
  speak(text, langCode) {
    if (!window.speechSynthesis || !text) return;
    // ยกเลิกเสียงเดิมก่อน (กันซ้อน)
    try { window.speechSynthesis.cancel(); } catch { }

    const u = new SpeechSynthesisUtterance(text);
    const voice = this.getVoiceFor(langCode);
    if (voice) u.voice = voice;
    u.lang = this.normalizeLang(langCode);
    u.rate = 1.0;   // ปรับได้ 0.5–2
    u.pitch = 1.0;  // ปรับได้ 0–2
    u.volume = 1.0; // 0–1
    window.speechSynthesis.speak(u);
  }
};

// โหลดเสียงเมื่อพร้อม
if ('speechSynthesis' in window) {
  Speech.loadVoices();
  window.speechSynthesis.onvoiceschanged = () => Speech.loadVoices();
}

// ===== Utilities: Time & WPM =====
function formatHMS(totalSeconds) {
  const s = Math.max(0, totalSeconds | 0);
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return (hh > 0)
    ? `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
    : `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}
function calcElapsedMs() {
  if (!startTime) return 0;
  return performance.now() - startTime;
}

function calcPlayTime() {
  return Math.floor(Math.max(0, calcElapsedMs()) / 1000);
}
function calcWPM() {
  const ms = calcElapsedMs();
  if (ms <= 0) return 0;
  const minutes = Math.max(ms / 60000, 1 / 60);
  const wpm = (correctChars / 5) / minutes;
  return Math.round(wpm);
}
function updateHUD() {
  hudTime.textContent = `⏱ เวลา: ${formatHMS(calcPlayTime())}`;
  hudWpm.textContent = `⌨️ WPM: ${calcWPM()}`;
  hudScore.textContent = `✅ ถูก: ${totalScore}/${maxWordsToPlay}`;
}

// ===== ส่งสถิติไป backend =====
function sendScore() {                                // 📤 ตามที่ขอ
  const totalSec = calcPlayTime();                    // เวลาสะสมจนถึงตอนนี้
  const deltaSec = Math.max(0, totalSec - lastSentSeconds); // ส่วนเพิ่มนับจากครั้งก่อน
  lastSentSeconds = totalSec;

  const payload = {
    total_words: 1,                                   // ส่งเพิ่มทีละ 1 คำ (สไตล์เดิม)
    wpm: calcWPM(),
    total_seconds: deltaSec                           // ส่งเป็น delta ให้ฝั่ง app.py บวกพอดี
  };

  console.log("[typing_game.js] POST /submit_score", payload);

  fetch("/submit_score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",                       // แนบคุกกี้ session ให้ชัวร์
    body: JSON.stringify(payload)
  })
    .then(r => r.json().catch(() => ({})))
    .then(d => console.log("[typing_game.js] submit_score response:", d))
    .catch(err => console.error("[typing_game.js] submit_score error:", err));
}

// ===== Render =====
function renderLetterBoxes(word, userInput = "", wrongIndex = -1) {
  letterBoxes.innerHTML = "";
  for (let i = 0; i < word.length; i++) {
    const box = document.createElement("div");
    box.className = "letter-box";
    if (userInput[i]) {
      if (i === wrongIndex) {
        box.classList.add("wrong"); box.textContent = userInput[i];
      } else if ((userInput[i] || "").toLowerCase() === (word[i] || "").toLowerCase()) {
        box.classList.add("correct"); box.textContent = userInput[i];
      } else {
        box.classList.add("wrong"); box.textContent = userInput[i];
      }
    } else {
      box.textContent = "";
    }
    letterBoxes.appendChild(box);
  }
}

function showWord() {
  if (index < words.length) {
    currentWordText = words[index];
    currentWord.textContent = (currentWordText || "").toUpperCase();
    userInput = "";
    translation.textContent = "";
    renderLetterBoxes(currentWordText, "");
    inputBox.value = "";
    inputBox.disabled = false;
    inputBox.focus();
    updateHUD();
  } else {
    // จบเกม: หยุด HUD แล้วสรุปผล
    if (tickIntervalId) { clearInterval(tickIntervalId); tickIntervalId = null; }
    const finalSeconds = calcPlayTime();
    const finalWpm = calcWPM();
    const finalTimeStr = formatHMS(finalSeconds);

    currentWord.textContent =
      `✅ Finished!\n ${totalScore}/${maxWordsToPlay} words • WPM ${finalWpm} • time ${finalTimeStr}`;
    letterBoxes.innerHTML = "";
    translation.textContent = "";
    console.log("[typing_game.js] finished", { totalScore, finalWpm, finalSeconds });
    // ไม่จำเป็นต้องยิงซ้ำตอนจบ (เราส่งทีละคำอยู่แล้ว) แต่ถ้าอยาก flush ก็เรียก sendScore() ได้อีกครั้ง
    showEndActions();
  }
}

// ========== Show End Actions (Restart / Leave) ==========
function showEndActions() {
  // ลบเดิมถ้ามี
  const old = document.getElementById('game-actions');
  if (old) old.remove();

  // สร้าง container ปุ่ม
  const wrap = document.createElement('div');
  wrap.id = 'game-actions';
  wrap.className = 'game-actions';

  // ปุ่ม Restart
  const btnRestart = document.createElement('button');
  btnRestart.className = 'game-btn';
  btnRestart.type = 'button';
  btnRestart.textContent = 'Restart';
  btnRestart.addEventListener('click', () => {
    // รีสตาร์ตหน้านี้ (รักษา query string เดิม)
    window.location.reload();
  });

  // ปุ่ม Leave
  const btnLeave = document.createElement('button');
  btnLeave.className = 'game-btn';
  btnLeave.type = 'button';
  btnLeave.textContent = 'Leave';
  btnLeave.addEventListener('click', () => {
    if (window.HOME_URL) {
      window.location.href = window.HOME_URL;
    } else {
      window.history.back();
    }
  });

  wrap.appendChild(btnRestart);
  wrap.appendChild(btnLeave);

  // แทรกไว้ใต้ current-word (หรือจะใส่ท้าย .content-area ก็ได้)
  const anchor = document.getElementById('current-word') || document.body;
  anchor.parentElement.insertBefore(wrap, anchor.nextSibling);
}

// ===== Input Handling =====
inputBox.addEventListener("input", () => {
  if (index >= words.length) return;

  // เริ่มจับเวลาทันทีที่พิมพ์ครั้งแรก (ไม่มีการจำกัดเวลา)
  if (!startTime) {
    startTime = performance.now();
    if (!tickIntervalId) tickIntervalId = setInterval(updateHUD, 250);
    updateHUD();
    console.log("[typing_game.js] timer started");
  }

  const word = words[index] || "";
  userInput = inputBox.value || "";

  let wrongIndex = -1;
  for (let i = 0; i < userInput.length; i++) {
    const ui = (userInput[i] || "").toLowerCase();
    const wi = (word[i] || "").toLowerCase();
    if (ui !== wi) { wrongIndex = i; break; }
  }

  // เล่นเสียงเมื่อกดตัวถูก
  if (
    userInput.length <= word.length &&
    (userInput[userInput.length - 1] || "").toLowerCase() === (word[userInput.length - 1] || "").toLowerCase()
  ) {
    TypingSound.currentTime = 0;
    TypingSound.play();
  }

  renderLetterBoxes(word, userInput, wrongIndex);

  if (wrongIndex !== -1) {
    wrongSound.currentTime = 0; wrongSound.play();
    userInput = userInput.slice(0, -1);
    inputBox.value = userInput;
    renderLetterBoxes(word, userInput);
    return;
  }

  // ถูกทั้งคำ
  if (userInput.length === word.length && userInput.toLowerCase() === word.toLowerCase()) {
    totalScore++;
    correctChars += word.length;   // นับตัวอักษรถูกเพื่อคำนวณ WPM

    // ยิงคะแนนทันที (แบบโค้ดเก่า) + log
    sendScore();

    // ขอคำแปล โดยส่งภาษาต้นทาง/ปลายทางไปด้วย
    fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        word: currentWordText,
        category: category,
        src_lang: srcLang,
        dest_lang: destLang
      })
    })
      .then(res => res.json())
      .then(data => {
        const transText = (data && data.translation) ? data.translation : "";
        translation.textContent = transText ? `Translation: ${transText}` : "";

        // ✅ เพิ่มรายการลงแถบประวัติ (ซ้าย)
        historyItems.push({
          src: currentWordText,
          dest: transText,
          t: Date.now(),
          wpm: calcWPM(),
          idx: index
        });
        renderHistory();

        // ไปคำถัดไป
        index++;
        inputBox.disabled = true;
        updateHUD();
        setTimeout(() => { showWord(); }, HOLD_MS);
      })
      .catch(() => {
        // เพิ่มประวัติแม้แปลไม่สำเร็จ (dest = "")
        historyItems.push({
          src: currentWordText,
          dest: "",
          t: Date.now(),
          wpm: calcWPM(),
          idx: index
        });
        renderHistory();

        index++;
        inputBox.disabled = true;
        updateHUD();
        setTimeout(() => { showWord(); }, HOLD_MS);
      });
  }
});

function renderHistory() {
  if (!historyList) return;
  historyList.innerHTML = "";

  // รายการใหม่อยู่บนสุด
  for (let i = historyItems.length - 1; i >= 0; i--) {
    const it = historyItems[i];

    const card = document.createElement('div');
    card.className = 'history-item';

    // กล่อง "ต้นฉบับ" ที่คลิกอ่านได้
    const srcEl = document.createElement('div');
    srcEl.className = 'history-src';
    const srcChip = document.createElement('button');
    srcChip.type = 'button';
    srcChip.className = 'speakable';
    srcChip.setAttribute('data-lang', window.srcLang || 'en');
    srcChip.setAttribute('data-text', it.src);
    srcChip.setAttribute('title', 'Click to speak');
    srcChip.innerHTML = `<span class="speak-icon">🔊</span><span>(${window.srcLang || 'src'}) ${it.src}</span>`;
    srcEl.appendChild(srcChip);

    // กล่อง "คำแปล" ที่คลิกอ่านได้ (ถ้ามี)
    const destEl = document.createElement('div');
    destEl.className = 'history-dest';
    if (it.dest) {
      const destChip = document.createElement('button');
      destChip.type = 'button';
      destChip.className = 'speakable';
      destChip.setAttribute('data-lang', window.destLang || 'th');
      destChip.setAttribute('data-text', it.dest);
      destChip.setAttribute('title', 'Click to speak');
      destChip.innerHTML = `<span class="speak-icon">🔊</span><span>(${window.destLang || 'dest'}) ${it.dest}</span>`;
      destEl.appendChild(destChip);
    } else {
      destEl.textContent = '→ (No translation)';
    }

    const metaEl = document.createElement('div');
    metaEl.className = 'history-meta';
    metaEl.textContent = `#${it.idx + 1} • WPM ~${it.wpm} • ${new Date(it.t).toLocaleTimeString()}`;

    card.appendChild(srcEl);
    card.appendChild(destEl);
    card.appendChild(metaEl);
    historyList.appendChild(card);
  }
}

// 🟢 วาง block นี้ต่อท้าย renderHistory()
if (historyList) {
  historyList.addEventListener('click', (e) => {
    const btn = e.target.closest('.speakable');
    if (!btn) return;
    const text = btn.getAttribute('data-text') || '';
    const lang = btn.getAttribute('data-lang') || 'en';
    if (text.trim()) {
      Speech.speak(text, lang);
      // ใส่เอฟเฟกต์เล็ก ๆ ให้ผู้ใช้เห็นว่ากดแล้ว
      btn.style.boxShadow = '0 0 0 2px rgba(0,255,0,.25)';
      setTimeout(() => { btn.style.boxShadow = ''; }, 250);
    }
  });
}
function openHistory() {
  if (!historyPanel) return;
  historyPanel.classList.add('open');
  historyPanel.setAttribute('aria-hidden', 'false');
  // 🔧 override inline style ที่ซ่อนอยู่
  historyPanel.style.transform = 'translateX(0)';
  historyPanel.style.zIndex = '2000'; // กันโดน navbar (z-index 1000) บัง
  console.log("[history] open");
}

function closeHistory() {
  if (!historyPanel) return;
  historyPanel.classList.remove('open');
  historyPanel.setAttribute('aria-hidden', 'true');
  // 🔧 ซ่อนไปเหมือนเดิม
  historyPanel.style.transform = 'translateX(-100%)';
  console.log("[history] close");
}

if (historyOpenBtn) historyOpenBtn.addEventListener('click', openHistory);
if (historyCloseBtn) historyCloseBtn.addEventListener('click', closeHistory);
// โฟกัส input ตลอด
document.addEventListener("click", () => inputBox.focus());


// เริ่มเกม
showWord();
