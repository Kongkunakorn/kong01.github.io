const TypingSound = new Audio("/static/sounds/Keyboard-02.wav");
const wrongSound = new Audio("/static/sounds/mixkit-cowbell-sharp-hit-1743.wav");

const words = window.words;
const category = window.category;
let index = 0;
let userInput = "";
let totalScore = 0;
let totalWordsTyped = 0; // เก็บจำนวนคำทั้งหมด
let startTime = null;
let endTime = null;

let maxWordsToPlay = words.length;
words.splice(maxWordsToPlay);

const currentWord = document.getElementById("current-word");
const translation = document.getElementById("translation");
const letterBoxes = document.getElementById("letter-boxes");
const inputBox = document.getElementById("hidden-input");

let currentWordText = words[index];
let currentIndex = 0;

function calcWPM() {
  if (!startTime) return 0;
  let elapsedMinutes = (Date.now() - startTime) / 60000;
  return Math.round(totalWordsTyped / elapsedMinutes);
}

function calcPlayTime() {
  if (!startTime) return 0;
  endTime = Date.now();
  let elapsedSeconds = Math.floor((endTime - startTime) / 1000);
  return elapsedSeconds;
}

function sendScore() {
  fetch("/submit_score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      total_words: 1,
      wpm: calcWPM(),
      total_seconds: calcPlayTime()
    })
  }).catch(err => console.error("ส่งข้อมูลผิดพลาด", err));
}

function renderLetterBoxes(word, userInput = "", wrongIndex = -1) {
  letterBoxes.innerHTML = "";
  for (let i = 0; i < word.length; i++) {
    const box = document.createElement("div");
    box.className = "letter-box";
    if (userInput[i]) {
      if (i === wrongIndex) {
        box.classList.add("wrong");
        box.textContent = userInput[i];
      } else if (userInput[i].toLowerCase() === word[i].toLowerCase()) {
        box.classList.add("correct");
        box.textContent = userInput[i];
      } else {
        box.classList.add("wrong");
        box.textContent = userInput[i];
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
    currentWord.textContent = currentWordText.toUpperCase();
    userInput = "";
    translation.textContent = "";
    renderLetterBoxes(currentWordText, "");
    inputBox.value = "";
    inputBox.focus();
  } else {
    currentWord.textContent = `✅ จบเกม! ✅\nคุณพิมพ์ถูก ${totalScore}/${maxWordsToPlay} คำ | WPM: ${calcWPM()}`;
    letterBoxes.innerHTML = "";
    translation.textContent = "";
  }
}

inputBox.addEventListener("input", () => {
  if (!startTime) startTime = Date.now();

  if (index >= words.length) return;
  const word = words[index];
  userInput = inputBox.value;

  let wrongIndex = -1;
  for (let i = 0; i < userInput.length; i++) {
    if (userInput[i].toLowerCase() !== word[i]?.toLowerCase()) {
      wrongIndex = i;
      break;
    }
  }

  if (
    userInput.length <= word.length &&
    userInput[userInput.length - 1]?.toLowerCase() ===
    word[userInput.length - 1]?.toLowerCase()
  ) {
    TypingSound.currentTime = 0;
    TypingSound.play();
  }

  renderLetterBoxes(word, userInput, wrongIndex);

  if (wrongIndex !== -1) {
    wrongSound.currentTime = 0;
    wrongSound.play();
    userInput = userInput.slice(0, -1);
    inputBox.value = userInput;
    renderLetterBoxes(word, userInput);
    return;
  }

  if (
    userInput.length === word.length &&
    userInput.toLowerCase() === word.toLowerCase()
  ) {
    totalScore++;
    totalWordsTyped++;

    sendScore();

    fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word: currentWordText, category })
    })
      .then(res => res.json())
      .then(data => {
        translation.textContent = `คำแปล: ${data.translation}`;
        index++;
        if (index >= words.length) {
          setTimeout(showWord, 500);
        } else {
          setTimeout(showWord, 500);
        }
      });
  }
});

document.addEventListener("click", () => inputBox.focus());

showWord();
