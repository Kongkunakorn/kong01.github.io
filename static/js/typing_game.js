const TypingSound = new Audio("/static/sounds/Keyboard-02.wav");
const wrongSound = new Audio("/static/sounds/mixkit-cowbell-sharp-hit-1743.wav");

const words = window.words;
const category = window.category;
let index = 0;
let userInput = "";
let totalScore = 0;


const currentWord = document.getElementById("current-word");
const translation = document.getElementById("translation");
const letterBoxes = document.getElementById("letter-boxes");
const inputBox = document.getElementById("hidden-input");

let currentWordText = words[index];
let currentIndex = 0;

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
    inputBox.focus(); // 👈 สำคัญ
  } else {
    currentWord.textContent = "✅ พิมพ์ครบแล้ว! ✅";
    letterBoxes.innerHTML = "";
    translation.textContent = "";

    fetch("/submit_score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room: category, score: totalScore }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ok") {
          window.location.href = `/leaderboard/${category}`;
        } else {
          alert("เกิดข้อผิดพลาดในการส่งคะแนน");
        }
      });
  }

}
inputBox.addEventListener("input", () => {
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

    fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word: currentWordText, category }),
    })
      .then((res) => res.json())
      .then((data) => {
        translation.textContent = `คำแปล: ${data.translation}`;
        index++;
        setTimeout(showWord, 1000);
      });

  }

});


document.addEventListener("click", () => inputBox.focus());

showWord();
