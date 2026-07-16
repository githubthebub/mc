/* ============================================================
   KINDRED ATLAS — game data
   All creatures, names, art and text are original.
   Real-world learning content is inspired by publicly known
   ideas from negotiation, charisma and behavioural science.
   ============================================================ */

const COUNTRIES = {
  london: {
    id: 'london',
    name: 'London',
    flag: '\u{1F1EC}\u{1F1E7}',
    tagline: 'Queues, drizzle and dry wit',
    ground: '#5c6b5e',
    path: '#8a8f84',
    accent: '#b03a3a',
    sky: '#9aa7b0',
    goods: { name: 'Ceylon Tea Chests', emoji: '\u{1F375}', value: 14 },
    localName: 'Mabel the Stallholder',
    merchantName: 'Mr. Pemberton (Merchant)',
    welcome: 'Mind the gap. Fancy a cuppa?'
  },
  usa: {
    id: 'usa',
    name: 'USA',
    flag: '\u{1F1FA}\u{1F1F8}',
    tagline: 'Big skies, small talk, bigger tips',
    ground: '#a8926a',
    path: '#8f7a54',
    accent: '#2e5f8a',
    sky: '#8fb8d8',
    goods: { name: 'Route 9 Vinyl Records', emoji: '\u{1F3B5}', value: 16 },
    localName: 'Darlene at the Diner',
    merchantName: 'Big Sal (Merchant)',
    welcome: 'Hey there! How’s it going?'
  },
  japan: {
    id: 'japan',
    name: 'Japan',
    flag: '\u{1F1EF}\u{1F1F5}',
    tagline: 'Quiet trains, deep bows, perfect craft',
    ground: '#7a8f6e',
    path: '#a89a8a',
    accent: '#c4485a',
    sky: '#e8d5da',
    goods: { name: 'Indigo Dye Textiles', emoji: '\u{1F9F5}', value: 18 },
    localName: 'Haruka-san',
    merchantName: 'Tanaka-san (Merchant)',
    welcome: 'Irasshaimase. Welcome, traveller.'
  },
  india: {
    id: 'india',
    name: 'India',
    flag: '\u{1F1EE}\u{1F1F3}',
    tagline: 'Colour, chai and the joyful art of the deal',
    ground: '#b08a52',
    path: '#c9a86a',
    accent: '#d4691e',
    sky: '#f0c987',
    goods: { name: 'Malabar Spice Tins', emoji: '\u{1F336}️', value: 15 },
    localName: 'Priya-ji',
    merchantName: 'Ravi Bhai (Merchant)',
    welcome: 'Namaste! Come, come — chai first, business after.'
  }
};

/* ---------- Creatures ("Kindred") — all original designs ---------- */
const CREATURES = [
  // London
  { id: 'nimbral',   name: 'Nimbral',   country: 'london', color: '#aebfd0', color2: '#7d93ab', art: 'wisp',
    blurb: 'A polite drizzle-spirit that follows umbrellas around Bloomsbury.', minFluency: 0, gather: 1 },
  { id: 'quibb',     name: 'Quibb',     country: 'london', color: '#c98a4b', color2: '#8a5a2b', art: 'tea',
    blurb: 'A round tea-sprite. Judges you silently if you microwave water.', minFluency: 0, gather: 1 },
  { id: 'whistlecap',name: 'Whistlecap',country: 'london', color: '#6b5b73', color2: '#4a3f52', art: 'chimney',
    blurb: 'A shy rooftop spirit. Only locals know where it perches.', minFluency: 40, gather: 2 },
  // USA
  { id: 'jukebop',   name: 'Jukebop',   country: 'usa', color: '#e05a8a', color2: '#9a2f5a', art: 'note',
    blurb: 'A neon diner-sprite that hums in 4/4 time and loves milkshakes.', minFluency: 0, gather: 1 },
  { id: 'prairieon', name: 'Prairieon', country: 'usa', color: '#8a6a3f', color2: '#5f4626', art: 'bison',
    blurb: 'A dust-mote spirit shaped like a tiny thundercloud with horns.', minFluency: 0, gather: 1 },
  { id: 'meteorette',name: 'Meteorette',country: 'usa', color: '#e8c34a', color2: '#b08a1e', art: 'star',
    blurb: 'A roadside-attraction star. Locals will point you to its billboard.', minFluency: 40, gather: 2 },
  // Japan
  { id: 'komorin',   name: 'Komorin',   country: 'japan', color: '#e8a04a', color2: '#b06a1e', art: 'lantern',
    blurb: 'A paper-lantern spirit that glows brighter when people speak kindly.', minFluency: 0, gather: 1 },
  { id: 'sakumo',    name: 'Sakumo',    country: 'japan', color: '#e8b4c8', color2: '#c07a9a', art: 'fox',
    blurb: 'A petal-fox that naps under blossom trees and collects lost buttons.', minFluency: 0, gather: 1 },
  { id: 'mochirin',  name: 'Mochirin',  country: 'japan', color: '#f0e8e0', color2: '#c8b8a8', art: 'mochi',
    blurb: 'A squishy rice-cake spirit. Bows back if you bow first.', minFluency: 40, gather: 2 },
  // India
  { id: 'barkha',    name: 'Barkha',    country: 'india', color: '#5a8ab0', color2: '#38617f', art: 'monsoon',
    blurb: 'A monsoon-wisp that smells of first rain on warm earth.', minFluency: 0, gather: 1 },
  { id: 'morvani',   name: 'Morvani',   country: 'india', color: '#2e8a7a', color2: '#1d5f54', art: 'peacock',
    blurb: 'A feather-spirit that fans out in emerald and sapphire when flattered.', minFluency: 0, gather: 1 },
  { id: 'rangoloo',  name: 'Rangoloo',  country: 'india', color: '#d4548a', color2: '#9a2f5f', art: 'pattern',
    blurb: 'A chalk-pattern spirit that redraws itself every dawn. Ask a local.', minFluency: 40, gather: 2 }
];

/* ---------- Negotiation rounds (befriending) ----------
   Each round: 1 correct technique + 2 plausible mistakes.
   `teach` text is the incidental learning payload.        */
const NEGOTIATION_ROUNDS = [
  {
    id: 'mirror',
    prompt: (n) => `The ${n} eyes you warily. “I’ve had travellers try to trap me before, you know.”`,
    options: [
      { good: true, text: '“…Try to trap you before?” (gently repeat their last words)',
        teach: 'MIRRORING — Chris Voss: repeat the last one-to-three words of what someone said, as a soft question. People instinctively elaborate and feel heard. It buys information and trust at zero cost.',
        note: 'mirror' },
      { good: false, text: '“I would never! I’m one of the good ones, honest!”',
        teach: 'Protesting your innocence makes the conversation about YOU. Defensiveness reads as guilt. Mirror their words instead — let them keep talking.' },
      { good: false, text: '“Forget those people. Look — I brought snacks!”',
        teach: 'A gift before trust reads as a bribe. Rapport first, incentives later.' }
    ]
  },
  {
    id: 'label',
    prompt: (n) => `The ${n} turns away. “Everyone just wants me to gather loot for them.”`,
    options: [
      { good: true, text: '“It seems like you’re worried I’d treat you as a tool, not a friend.”',
        teach: 'LABELING — Chris Voss: name the emotion out loud (“It seems like… It sounds like…”). Naming a fear defuses it; the brain calms down when feelings are acknowledged rather than argued with.',
        note: 'label' },
      { good: false, text: '“No, no — you’ve got me all wrong!”',
        teach: 'Telling someone their feeling is wrong makes them defend it harder. Never argue with an emotion — label it.' },
      { good: false, text: '“Well… gathering IS what you’re best at…”',
        teach: 'You just confirmed their exact fear. Listen for the feeling underneath the words, not the literal words.' }
    ]
  },
  {
    id: 'calibrated',
    prompt: (n) => `“Travelling the whole world sounds exhausting,” the ${n} sighs. “Why would I ever join you?”`,
    options: [
      { good: true, text: '“What would make travelling together feel worth it for you?”',
        teach: 'CALIBRATED QUESTIONS — Chris Voss: open questions starting with “How” or “What” give the other side the illusion of control while they solve YOUR problem. Never ask questions answerable with “no”.',
        note: 'calibrated' },
      { good: false, text: '“Because I’m going to be the greatest traveller ever!”',
        teach: 'Your dream is not their reason. People move for THEIR motives, not yours.' },
      { good: false, text: '“So… will you join me? Yes or no?”',
        teach: 'Closed questions corner people, and cornered people say no. Open the door with How/What questions instead.' }
    ]
  },
  {
    id: 'audit',
    prompt: (n) => `You step closer. The ${n} tenses, ready to bolt.`,
    options: [
      { good: true, text: '“You probably think I’m another loud stranger who wants something from you.”',
        teach: 'ACCUSATION AUDIT — Chris Voss: say the worst things they could think about you BEFORE they do. Objections named in advance lose their sting; honesty this blunt builds instant credibility.',
        note: 'audit' },
      { good: false, text: '“Don’t run! I’m friendly, I swear!”',
        teach: 'Shouting reassurance at a nervous creature is still shouting. Lower the temperature; don’t raise your voice.' },
      { good: false, text: 'Creep closer very slowly and quietly…',
        teach: 'You cannot sneak up on trust. Transparency beats stealth in every relationship.' }
    ]
  },
  {
    id: 'thatsright',
    prompt: (n) => `“I just want somewhere I belong,” the ${n} murmurs, “where what I do actually means something.”`,
    options: [
      { good: true, text: 'Summarise it back: “You want to matter to someone — not just be useful.”',
        teach: '“THAT’S RIGHT” — Chris Voss: summarise their world so well they say “that’s right.” It’s the moment a negotiation turns. (Beware “you’re right” — that’s what people say to make you go away.)',
        note: 'thatsright' },
      { good: false, text: '“You’re right! And you’ll be super useful to me!”',
        teach: '“You’re right” is a brush-off, and you immediately made it about usefulness — their exact fear.' },
      { good: false, text: '“Belonging is overrated. Adventure is where it’s at!”',
        teach: 'Dismissing someone’s core need ends negotiations. Empathy isn’t agreeing — it’s understanding.' }
    ]
  },
  {
    id: 'conviction',
    prompt: (n) => `The ${n} squares up. “Give me one reason to believe a word you say.”`,
    options: [
      { good: true, text: 'Pause. Hold their gaze. Then, slowly and warmly: “I keep my promises to my friends.”',
        teach: 'CONVICTION — Charlie Houpert (Charisma on Command): confidence is carried in the delivery — pause before you speak, slow down, finish sentences with a downward tone. Warmth plus certainty beats a list of credentials.',
        note: 'conviction' },
      { good: false, text: 'Rattle off your achievements as fast as possible.',
        teach: 'Speed reads as nerves. A fire-hose of credentials persuades nobody; composure does.' },
      { good: false, text: 'Shrug. “I dunno… I’m pretty great, I guess?”',
        teach: 'Hedging words (“I guess”, “kinda”, “maybe”) leak doubt. If YOU don’t sound convinced, nobody else will be.' }
    ]
  },
  {
    id: 'djvoice',
    prompt: (n) => `The ${n} is agitated — crackling, pacing, sparks flying everywhere.`,
    options: [
      { good: true, text: 'Lower your voice — slow, calm, downward tone: “Take your time. I’m not going anywhere.”',
        teach: 'THE LATE-NIGHT FM DJ VOICE — Chris Voss: a slow, calm, downward-inflected voice tells the other brain “the situation is under control.” Calm is contagious. So is panic — choose which one you spread.',
        note: 'djvoice' },
      { good: false, text: 'Match their energy! “HEY! HEY! IT’S OKAY!!”',
        teach: 'Meeting agitation with volume is pouring petrol on it. Your tone sets the thermostat of the conversation.' },
      { good: false, text: 'Laugh nervously and hope it passes.',
        teach: 'Nervous laughter signals that even YOU think things are out of control.' }
    ]
  }
];

/* ---------- Cultural fluency scenarios ---------- */
const CULTURE_SCENARIOS = {
  london: [
    { id: 'ldn_queue', q: 'A crowd waits at the bus stop. Where do you stand?',
      options: [
        { good: true, text: 'Find the end of the queue and join it.',
          why: 'Queueing is sacred in Britain — an unwritten social contract. Jumping it is one of the few things that will make Londoners openly cross.' },
        { good: false, text: 'Stand wherever — it’s a free country.',
          why: 'There IS a queue, even when it doesn’t look like one. Britons silently track exactly who arrived when.' },
        { good: false, text: 'Slip toward the front — you’re in a hurry.',
          why: 'Queue-jumping is close to a criminal offence in the British social code. Tuts will be deployed.' }
      ] },
    { id: 'ldn_alright', q: 'A colleague passes and says, “You alright?” What do they want?',
      options: [
        { good: true, text: 'It’s just a greeting — reply “Yeah, you?” and carry on.',
          why: '“You alright?” is the London “hello”. Nobody is asking for your medical history — mirror it back and keep walking.' },
        { good: false, text: 'Explain in detail how you’ve actually been feeling.',
          why: 'They meant “hi”. A full wellness report will cause visible panic.' },
        { good: false, text: '“Why? Do I look ill?”',
          why: 'Taking it literally marks you as a newcomer. It’s a ritual phrase, not a question.' }
      ] },
    { id: 'ldn_round', q: 'You’re at the pub with three new friends. The first two bought drinks for the whole table. Your move?',
      options: [
        { good: true, text: 'Buy the next round for everyone — it’s your turn.',
          why: 'The round system is British social currency. Skipping your round is remembered FOREVER. Reciprocity builds trust everywhere — the pub just formalised it.' },
        { good: false, text: 'Buy a drink just for yourself.',
          why: 'Sitting out of the rounds marks you as a freeloader. The system only works because everyone takes a turn.' },
        { good: false, text: 'Announce that rounds are economically inefficient.',
          why: 'Technically true, socially fatal. Rory Sutherland would note: the inefficiency IS the point — it’s a costly signal of friendship.' }
      ] },
    { id: 'ldn_weather', q: 'A stranger at the market says, “Bit grim out today, isn’t it?”',
      options: [
        { good: true, text: '“Ooh, dreadful. Supposed to clear up Thursday, mind.”',
          why: 'Weather talk is Britain’s social handshake — a safe ritual for strangers to signal friendliness. Join the ritual; it’s never really about the weather.' },
        { good: false, text: '“It’s just weather. Who cares?”',
          why: 'You rejected a friendship offer. Weather chat is an invitation, not a meteorology seminar.' },
        { good: false, text: 'Deliver a 5-minute lecture on cloud formation.',
          why: 'The ritual wants participation, not expertise. Match the register: brief, wry, mildly pessimistic.' }
      ] }
  ],
  usa: [
    { id: 'usa_tip', q: 'Your diner breakfast was $20 and the server was friendly. The bill arrives.',
      options: [
        { good: true, text: 'Add an 18–22% tip.',
          why: 'In the USA, servers’ wages are built around tips — roughly 20% is standard, not generous. Skipping it isn’t thrifty, it’s taking their pay.' },
        { good: false, text: 'Pay exactly $20 — the price is the price.',
          why: 'Unlike Japan or much of Europe, US service jobs depend on tips. Leaving none is a loud insult.' },
        { good: false, text: 'Leave 5% — that seems like plenty.',
          why: 'A tiny tip reads worse than none — it says “I know the custom and judged you unworthy.” 18–22% is the floor for decent service.' }
      ] },
    { id: 'usa_smalltalk', q: 'The cashier beams: “Hey! How’s it going?”',
      options: [
        { good: true, text: '“Great, thanks! How about you?” — warm, brief, upbeat.',
          why: 'American small talk runs warm and positive. It’s a friendliness ping, not an inquiry — return the energy and keep it short.' },
        { good: false, text: 'Give an honest, detailed account of your morning.',
          why: 'It’s a ritual greeting. The expected answer is upbeat and under three seconds.' },
        { good: false, text: 'Say nothing — you don’t know this person.',
          why: 'Silence reads as hostility in the US, where strangers chat easily. A smile and “great, you?” costs nothing.' }
      ] },
    { id: 'usa_direct', q: 'You’re pitching your goods to an American buyer. How do you open?',
      options: [
        { good: true, text: 'Friendly hello, then straight to the point: what it is, why it’s great.',
          why: 'US business culture prizes directness and optimism — lead with the headline. Long ceremonial preambles read as evasive.' },
        { good: false, text: 'Twenty minutes of formal pleasantries before mentioning business.',
          why: 'What builds trust in some cultures reads as time-wasting here. In the US, getting to the point IS the courtesy.' },
        { good: false, text: 'Open by asking their salary and who they voted for.',
          why: 'Americans chat easily but money and politics with strangers are landmines. Stick to sports, food, travel, weather.' }
      ] },
    { id: 'usa_space', q: 'You’re chatting with a new American acquaintance. How close do you stand?',
      options: [
        { good: true, text: 'About an arm’s length away.',
          why: 'US personal space runs larger than much of the world — roughly an arm’s length for acquaintances. Closer feels pushy; a step back reads as polite, not cold.' },
        { good: false, text: 'Shoulder to shoulder — shows warmth!',
          why: 'They will keep stepping backwards and you will chase them across the room. Watch their feet: if they retreat, you’re too close.' },
        { good: false, text: 'Across the room, shouting.',
          why: 'Distance can be as awkward as closeness. Arm’s length, easy eye contact, relaxed smile.' }
      ] }
  ],
  japan: [
    { id: 'jpn_bow', q: 'You meet Tanaka-san, an older merchant, for the first time.',
      options: [
        { good: true, text: 'A small bow, slightly lower and longer because he’s senior.',
          why: 'The bow is Japan’s handshake — depth and duration signal respect, and seniority earns a deeper one. When unsure, a modest bow is never wrong.' },
        { good: false, text: 'Firm handshake and a hearty slap on the back.',
          why: 'Uninvited touching is jarring in Japan. Many will politely endure it — politely enduring things is a national art — but you’ve marked yourself as unaware.' },
        { good: false, text: 'Casual wave: “Yo, Tanaka!”',
          why: 'First names without honorifics are for close friends. Use the family name + “san”: Tanaka-san.' }
      ] },
    { id: 'jpn_meishi', q: 'Tanaka-san offers you his business card (meishi) with both hands.',
      options: [
        { good: true, text: 'Receive it with both hands, read it carefully, place it neatly before you.',
          why: 'The meishi is treated as an extension of the person. Both hands, a moment of genuine attention, and careful placement signal deep respect. It’s ritual — and ritual is meaning.' },
        { good: false, text: 'Take it one-handed and pocket it without looking.',
          why: 'Pocketing a card unread is like ignoring an outstretched hand. The card IS the person, ritually speaking.' },
        { good: false, text: 'Jot your shopping list on the back of it.',
          why: 'Writing on someone’s meishi in front of them is close to scribbling on their face. Treat it like a small gift.' }
      ] },
    { id: 'jpn_tip', q: 'After a wonderful meal in Kyoto, you want to thank the staff.',
      options: [
        { good: true, text: 'No tip — a sincere “gochisōsama deshita” (thanks for the feast) on the way out.',
          why: 'Japan doesn’t tip — excellent service is the baseline, already in the price. Cash left behind may cause confusion or even offence; gratitude is spoken, not paid.' },
        { good: false, text: 'Leave a 20% tip like back home.',
          why: 'Staff may chase you down the street to return your “forgotten” money. Service excellence here isn’t bought — it’s a matter of pride.' },
        { good: false, text: 'Haggle over the bill — it worked in the bazaar!',
          why: 'Prices in Japan are fixed and haggling over a restaurant bill is deeply awkward. Save your bargaining for markets that expect it.' }
      ] },
    { id: 'jpn_train', q: 'You board a packed Tokyo train and your phone starts ringing.',
      options: [
        { good: true, text: 'Silence it immediately; text instead. Keep your voice low.',
          why: 'Japanese trains run on shared quiet — phones on “manner mode”, calls not taken. Public space is treated as everyone’s living room, and consideration is the rent.' },
        { good: false, text: 'Answer it — keep it under ten minutes.',
          why: 'A phone call on a Japanese train draws the kind of silence that has weight. Manner mode exists for a reason.' },
        { good: false, text: 'Put it on speaker so your hands are free.',
          why: 'Congratulations: you are now the main character of everyone’s worst commute.' }
      ] }
  ],
  india: [
    { id: 'ind_haggle', q: 'A bazaar seller quotes ₹500 for a scarf you like. What now?',
      options: [
        { good: true, text: 'Smile and counter warmly around ₹250 — enjoy the back-and-forth.',
          why: 'In Indian bazaars, haggling is the expected ritual — a social game both sides enjoy. The first price is an opening move, not an insult, and neither is your counter. Meet in the middle with a smile.' },
        { good: false, text: 'Pay ₹500 — haggling feels rude.',
          why: 'You just paid the “tourist opening price”. Refusing to haggle can even disappoint the seller — you skipped the fun part.' },
        { good: false, text: 'Act insulted and storm off.',
          why: 'The quote wasn’t an offence, it was an invitation. Walking away slowly can be a tactic — storming off just ends the game.' }
      ] },
    { id: 'ind_chai', q: 'Mid-negotiation, the shop owner pauses and offers you chai.',
      options: [
        { good: true, text: 'Accept gratefully and chat about family, cricket, life.',
          why: 'In India, relationship comes before transaction. The chai IS the negotiation — refusing hospitality to “save time” usually costs you the deal and the friendship.' },
        { good: false, text: 'Decline: “Let’s keep this professional and quick.”',
          why: 'You just declined the relationship, not the tea. Business here flows through trust, and trust flows through hospitality.' },
        { good: false, text: '“No chai — but knock 10% off instead?”',
          why: 'Converting hospitality into a discount demand is a spectacular way to sour the room. Accept the tea; the discount often follows on its own.' }
      ] },
    { id: 'ind_hand', q: 'You’re sharing a thali meal eaten by hand. Which hand do you use?',
      options: [
        { good: true, text: 'The right hand.',
          why: 'Across India, the right hand is for eating and giving; the left is traditionally considered unclean. The same rule guides handing over money and gifts.' },
        { good: false, text: 'The left — you’re left-handed, it’s natural.',
          why: 'Tradition still expects the right hand for food and exchange. Left-handers manage with the right in shared meals — locals will quietly appreciate it.' },
        { good: false, text: 'Both hands at once — efficiency!',
          why: 'Enthusiastic, but no. Right hand for the food; left hand stays in your lap.' }
      ] },
    { id: 'ind_wobble', q: 'You ask the driver, “Can you take me to the fort?” He tilts his head side to side in a smooth wobble.',
      options: [
        { good: true, text: 'That’s the famous head wobble — usually “yes” or “OK, understood”. Hop in.',
          why: 'The Indian head wobble mostly signals agreement or acknowledgement — context and enthusiasm tell you which. A brisk wobble with a smile is a warm yes.' },
        { good: false, text: 'He’s refusing — find another driver.',
          why: 'You just walked away from a yes. The side-to-side wobble is not the Western head-shake “no”.' },
        { good: false, text: 'Wobble back harder until someone wins.',
          why: 'Charming attempt, but it’s a gesture, not a duel. (Locals may find your effort endearing, though.)' }
      ] }
  ]
};

/* ---------- Market haggle steps (selling your goods) ---------- */
const HAGGLE = {
  anchor: {
    prompt: (m) => `${m} looks over your goods. “So… what are you asking for the lot?”`,
    options: [
      { id: 'high', text: 'Anchor HIGH — name a bold price and hold their gaze.',
        teach: 'ANCHORING — the first number spoken exerts gravity over the whole negotiation. A confident high anchor drags the final price up … but an anchor without credibility can snap.' },
      { id: 'fair', text: 'Name a fair, middle-of-the-road price.',
        teach: 'Safe, but you’ve left money on the table — the counterpart was braced for a higher opener. The first number sets the range; make it work for you.' },
      { id: 'low',  text: 'Start low so they can’t say no.',
        teach: 'A low anchor works against YOU — you’ve capped your own ceiling before they said a word. Cheapness also signals low quality (Sutherland: price is a story about value).' }
    ]
  },
  counter: {
    prompt: (m, offer) => `${m} strokes their chin. “Hmm. I’ll give you ${offer} — final offer.”`,
    options: [
      { id: 'calibrated', text: '“How am I supposed to accept that and still feed my Kindred?”',
        teach: 'The calibrated “How” question (Voss) hands them your problem without saying no. “Final offers” usually aren’t — and now they’re negotiating against themselves.' },
      { id: 'split', text: '“Let’s just split the difference.”',
        teach: 'NEVER SPLIT THE DIFFERENCE — Voss’s book title exists for a reason. Splitting feels fair but rewards whoever anchored more aggressively (them), and signals your numbers were padding all along.' },
      { id: 'accept', text: '“Fine, deal.” (accept their counter)',
        teach: 'Accepting the first counter leaves value behind and teaches the merchant that pressure works on you. In repeated games, that’s expensive.' }
    ]
  },
  close: {
    prompt: (m) => `${m} makes a final number and watches you. The silence stretches…`,
    options: [
      { id: 'silence', text: 'Say nothing. Let the silence do the work.',
        teach: 'STRATEGIC SILENCE — most people fear silence more than concession. Hold it a beat longer than comfortable and watch offers improve themselves.' },
      { id: 'eager', text: '“DEAL! Yes! Absolutely! Thank you!!”',
        teach: 'Eagerness at the close tells them they overpaid you — next time their opener will be lower. Close warmly, but close CALM.' },
      { id: 'squeeze', text: '“Throw in free delivery and your hat, and we’re done.”',
        teach: 'Grabbing the last crumb wins pennies and loses the relationship. Leave something on the table — the best negotiators are the ones people WANT to deal with again.' }
    ]
  }
};

/* ---------- Field notes (the journal) ---------- */
const FIELD_NOTES = {
  mirror:      { title: 'Mirroring',                source: 'Chris Voss · Never Split the Difference' },
  label:       { title: 'Labeling emotions',        source: 'Chris Voss · Never Split the Difference' },
  calibrated:  { title: 'Calibrated How/What questions', source: 'Chris Voss · Never Split the Difference' },
  audit:       { title: 'The accusation audit',     source: 'Chris Voss · Never Split the Difference' },
  thatsright:  { title: '“That’s right” beats “you’re right”', source: 'Chris Voss · Never Split the Difference' },
  djvoice:     { title: 'The late-night FM DJ voice', source: 'Chris Voss · Never Split the Difference' },
  conviction:  { title: 'Speak with conviction',    source: 'Charlie Houpert · Charisma on Command' },
  anchor:      { title: 'Anchoring the first number', source: 'Behavioural economics · negotiation' },
  split:       { title: 'Never split the difference', source: 'Chris Voss' },
  silence:     { title: 'Strategic silence',        source: 'Negotiation craft' },
  frame:       { title: 'Framing & provenance',     source: 'Rory Sutherland · Alchemy' },
  signal:      { title: 'Costly signaling',         source: 'Rory Sutherland · Alchemy' },
  arbitrage:   { title: 'Distance creates value',   source: 'Economics of trade' },
  psychologic: { title: 'Psycho-logic',             source: 'Rory Sutherland · Alchemy' }
};

const SUTHERLAND_NOTES = {
  frame: 'FRAMING & PROVENANCE — Rory Sutherland: value lives in the mind, not the object. The same tea sells for triple with a story attached (“hand-picked at dawn on the estate’s north slope”). You are never selling goods; you are selling meaning.',
  signal: 'COSTLY SIGNALING — Rory Sutherland: the tailored suit works BECAUSE it was expensive. Signals must cost something to be believed — flowers, diamonds, and hand-written notes all persuade precisely because they are inefficient.',
  arbitrage: 'DISTANCE CREATES VALUE — goods carried far from home carry scarcity and story with them. London tea is ordinary in London and exotic in Osaka. Traders have monetised “faraway-ness” for five thousand years.',
  psychologic: 'PSYCHO-LOGIC — Rory Sutherland: the opposite of a good idea can be another good idea. Humans don’t buy with spreadsheets; they buy with meaning, context and story. If a thing makes no economic sense but everyone does it — look for the hidden psychological sense.'
};

/* ---------- Shop upgrades ---------- */
const UPGRADES = [
  { id: 'suit', name: 'Tailored Suit', price: 250, emoji: '\u{1F454}',
    desc: 'One mistake per Kindred negotiation is forgiven. A costly signal that you mean business.',
    note: 'signal' },
  { id: 'story', name: 'Provenance Story Cards', price: 180, emoji: '\u{1F4DC}',
    desc: 'Hand-lettered cards telling each good’s origin story. High anchors always land as credible.',
    note: 'frame' },
  { id: 'ledger', name: 'Merchant’s Ledger', price: 400, emoji: '\u{1F4D2}',
    desc: 'Track provenance and reputation. All sale prices +25%.',
    note: 'psychologic' },
  { id: 'teaset', name: 'Traveller’s Tea Set', price: 150, emoji: '\u{1FAD6}',
    desc: 'Your Kindred gather 25% faster. Hospitality makes everyone work happier.',
    note: null }
];

const TRAVEL_COST = 40;
const GATHER_INTERVAL_MS = 8000;
