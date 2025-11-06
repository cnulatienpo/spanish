const spanishLexiconCache = {
  set: null
};

export function mixCefrDefaultMin(cefr) {
  const c = String(cefr || '').toUpperCase();
  if (c === 'A0') return 1;
  if (c === 'A1') return 2;
  if (c === 'A2') return 3;
  if (c === 'B1') return 5;
  if (c === 'B2') return 7;
  if (c === 'C1') return 10;
  if (c === 'C2') return 12;
  return 2;
}

export function tokenize(str) {
  let s = (str || '').toLowerCase();
  const punct = '.,!?;:"()[]{}¿¡';
  for (let i = 0; i < punct.length; i++) {
    const ch = punct[i];
    s = s.split(ch).join(' ');
  }
  while (s.includes('  ')) s = s.replace(/  +/g, ' ');
  s = s.trim();
  if (!s) return [];
  return s.split(' ');
}

export function spanishLexicon() {
  if (!spanishLexiconCache.set) {
    spanishLexiconCache.set = new Set([
      'hola','adios','gracias','por','para','porque','pero','tambien','muy','mas','menos',
      'si','no','yo','tu','usted','el','ella','nosotros','ustedes','ellos',
      'me','te','se','lo','la','los','las','le','les',
      'de','del','al','en','con','sin','sobre','entre','hasta','desde',
      'como','cuando','donde','quien','que','cual','cuanto',
      'ser','estar','tener','hacer','poder','ir','ven','venir','quiero','puedo','tengo',
      'bien','mal','mucho','poco','aqui','alli','hoy','ayer','manana',
      '¿','¡'
    ]);
  }
  return spanishLexiconCache.set;
}

export function expectedSet(expectedList) {
  const set = new Set();
  if (Array.isArray(expectedList)) {
    for (const item of expectedList) {
      const toks = tokenize(item);
      for (const t of toks) set.add(t);
    }
  }
  return set;
}

export function hasDiacritic(token) {
  return /[áéíóúñ]/.test(token);
}

export function isSpanishToken(token, expectedSetRef) {
  const t = token || '';
  if (hasDiacritic(t)) return true;
  if (t === '¿' || t === '¡') return true;
  if (expectedSetRef && expectedSetRef.has(t)) return true;
  if (spanishLexicon().has(t)) return true;
  return false;
}

export function countSpanishTokens(user, expectedList) {
  const toks = tokenize(user);
  const set = expectedSet(expectedList);
  let count = 0;
  for (const tok of toks) {
    if (isSpanishToken(tok, set)) count++;
  }
  return count;
}

export function overlapQuality(user, expectedList) {
  if (!Array.isArray(expectedList) || expectedList.length === 0) return 0;
  const userTokens = new Set(tokenize(user));
  let hits = 0;
  for (const phrase of expectedList) {
    const tokens = tokenize(phrase);
    const hasHit = tokens.some(t => userTokens.has(t));
    if (hasHit) hits++;
  }
  return hits / Math.max(1, expectedList.length);
}

export function scoreLadder(user, seeder) {
  const targets = seeder?.targets || {};
  const expected = Array.isArray(targets.expected_spanish) ? targets.expected_spanish : [];
  const mix = seeder?.mix || {};
  const min = (typeof mix.min_tokens === 'number')
    ? mix.min_tokens
    : mixCefrDefaultMin(seeder?.cefr);
  const used = countSpanishTokens(user, expected);
  const pass = used >= min;
  const quality = overlapQuality(user, expected);
  let code = 'PASS';
  if (!pass) code = 'ADD_ONE_MORE';
  else if (quality > 0.9) code = 'PERFECTO';
  else if (quality > 0.6) code = 'CLOSE';
  const need = Math.max(0, min - used);
  return {
    pass,
    min,
    used,
    need,
    quality,
    code
  };
}
