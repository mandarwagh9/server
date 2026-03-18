const WORDS = {
  animals: [
    "elephant", "giraffe", "penguin", "dolphin", "kangaroo", "octopus", "butterfly",
    "crocodile", "flamingo", "gorilla", "hedgehog", "jellyfish", "koala", "leopard",
    "meerkat", "narwhal", "ostrich", "peacock", "raccoon", "salamander", "toucan",
    "walrus", "axolotl", "badger", "camel", "donkey", "eagle", "falcon", "gecko",
    "hamster", "iguana", "jaguar", "lemur", "mammoth", "newt", "orca", "parrot",
    "quail", "raven", "squirrel", "tapir", "urchin", "vulture", "wombat", "yak",
    "zebra", "beaver", "crane", "dingo", "emu", "fox", "goat", "heron", "ibis"
  ],
  food: [
    "pizza", "hamburger", "spaghetti", "sandwich", "pancakes", "sushi", "taco",
    "burrito", "croissant", "donut", "hotdog", "noodles", "popcorn", "pretzel",
    "ramen", "steak", "waffle", "avocado", "broccoli", "carrot", "eggplant",
    "fries", "grapes", "honey", "icecream", "jelly", "ketchup", "lemonade",
    "mango", "nachos", "olive", "pasta", "quesadilla", "rice", "soup", "toast",
    "utensils", "vegetable", "watermelon", "banana", "cereal", "dumpling",
    "espresso", "fruit", "garlic", "hummus", "instant", "juice", "kale"
  ],
  objects: [
    "umbrella", "telescope", "lighthouse", "scissors", "headphones", "keyboard",
    "backpack", "camera", "flashlight", "glasses", "helicopter", "island", "jeans",
    "kite", "ladder", "mirror", "notebook", "pencil", "quarter", "radio", "satellite",
    "telephone", "usb", "video", "wallet", "anchor", "balloon", "candle", "door",
    "envelope", "flag", "guitar", "hammer", "iron", "jigsaw", "knife", "lamp",
    "magnet", "needle", "origami", "paintbrush", "quilt", "rope", "sword", "thread"
  ],
  actions: [
    "dancing", "sleeping", "flying", "swimming", "cooking", "reading", "writing",
    "painting", "climbing", "jumping", "running", "walking", "singing", "laughing",
    "crying", "thinking", "fishing", "hunting", "camping", "surfing", "skiing",
    "bowling", "boxing", "cycling", "diving", "eating", "fighting", "gardening",
    "hiking", "juggling", "knitting", "laughing", "mowing", "napping", "opening",
    "pushing", "questioning", "resting", "shaving", "throwing", "typing"
  ],
  nature: [
    "mountain", "volcano", "waterfall", "tornado", "rainbow", "thunder", "lightning",
    "blizzard", "avalanche", "sunset", "sunrise", "moonlight", "starry", "cloudy",
    "rainy", "windy", "foggy", "icy", "rocky", "sandy", "grassy", "forest",
    "jungle", "desert", "canyon", "valley", "island", "river", "lake", "ocean",
    "beach", "cave", "cliff", "glacier", "meadow", "swamp", "coral", "reef",
    "tide", "wave", "pond", "stream", "ridge", "summit", "trail"
  ],
  random: [
    "pirate", "wizard", "robot", "alien", "zombie", "vampire", "ninja", "dragon",
    "unicorn", "ghost", "mermaid", "werewolf", "knight", "wizard", "castle",
    "crown", "diamond", "engine", "factory", "ghost", "hospital", "jail", "kitchen",
    "library", "museum", "nightmare", "office", "palace", "prison", "quarry",
    "radar", "sewer", "temple", "universe", "village", "wedding", "yacht", "zoo"
  ]
};

function getRandomWord() {
  const categories = Object.keys(WORDS);
  const category = categories[Math.floor(Math.random() * categories.length)];
  const words = WORDS[category];
  const word = words[Math.floor(Math.random() * words.length)];
  return word;
}

function getWords(count = 3) {
  const allWords = [];
  for (const cat of Object.keys(WORDS)) {
    allWords.push(...WORDS[cat]);
  }
  const shuffled = allWords.sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

function obfuscateWord(word, knownIndices = []) {
  return word.split('').map((char, i) => {
    if (knownIndices.includes(i)) return char;
    return '_';
  }).join(' ');
}

module.exports = { WORDS, getRandomWord, getWords, obfuscateWord };
