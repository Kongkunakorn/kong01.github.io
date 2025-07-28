const TypingSound = new Audio("/static/sounds/Keyboard-02.wav");
const wrongSound = new Audio(
  "/static/sounds/mixkit-cowbell-sharp-hit-1743.wav"
);
const words = window.words;
let index = 0;
let userInput = "";

const currentWord = document.getElementById("current-word");
const translation = document.getElementById("translation");
const letterBoxes = document.getElementById("letter-boxes");

const category = window.category;
let currentWordText = words[index];
let currentIndex = 0;
currentWord.textContent = currentWordText;

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
    currentWord.textContent = words[index].toUpperCase();
    userInput = "";
    translation.textContent = "";
    renderLetterBoxes(words[index], userInput);
  } else {
    currentWord.textContent = "✅พิมพ์ครบแล้ว!✅";
    letterBoxes.innerHTML = "";
  }
}

document.addEventListener("keydown", (e) => {
  if (index >= words.length) return;
  let word = words[index];

  if (/^[a-zA-Z]$/.test(e.key) && userInput.length < word.length) {
    userInput += e.key;
    let lastIndex = userInput.length - 1;
    if (
      userInput[lastIndex] &&
      userInput[lastIndex].toLowerCase() === word[lastIndex].toLowerCase()
    ) {
      TypingSound.currentTime = 0;
      TypingSound.play();
    }
  } else if (e.key === "Backspace" && userInput.length > 0) {
    userInput = userInput.slice(0, -1);
  } else {
    return;
  }

  let wrongIndex = -1;
  for (let i = 0; i < userInput.length; i++) {
    if (userInput[i].toLowerCase() !== word[i].toLowerCase()) {
      wrongIndex = i;
      break;
    }
  }

  renderLetterBoxes(word, userInput, wrongIndex);

  if (wrongIndex !== -1) {
    wrongSound.currentTime = 0;
    wrongSound.play();
    setTimeout(() => {
      userInput = userInput.slice(0, -1);
      renderLetterBoxes(word, userInput);
    }, 400);
    return;
  }
  if (
    userInput.length === word.length &&
    userInput.toLowerCase() === word.toLowerCase()
  ) {
    fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word: currentWordText, category: category }), // Using the category variable
    })
      .then((response) => response.json())
      .then((data) => {
        translation.textContent = `คำแปล: ${data.translation}`;
        index++;
        setTimeout(showWord, 1000);
      });
  }
});

showWord();
