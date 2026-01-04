#!/usr/bin/env python3
"""
Neal-like Password Game (edit-in-place)
- Type an initial password to satisfy level 1.
- Each time you pass active rules, the next rule unlocks.
- You continue editing the same password to satisfy stacked rules.
Commands:
  hint  -> hint for the first failing rule (uses current attempt)
  show  -> display active rules
  quit  -> exit the game
"""

import string
import math
import random

# ---------------------
# Helpers & constants
# ---------------------
EMOJIS = "😀😂🤣😍🥰😎👍🔥💀🎉💡🤯🥵🥶🫣🫡"
SPECIALS = "!@#$%^&*()-_+="
MONTHS = ["january","february","march","april","may","june","july","august",
          "september","october","november","december"]

def is_fibonacci(n):
    if n < 0: return False
    a, b = 0, 1
    while b < n:
        a, b = b, a + b
    return n == 0 or n == b

def count_vowels(s):
    return sum(1 for c in s if c.lower() in "aeiou")

def count_consonants(s):
    return sum(1 for c in s if c.isalpha() and c.lower() not in "aeiou")

# ---------------------
# Rule factories (each maker(prev) -> (check_fn, description, hint_fn))
# ---------------------
def length_at_least_factory(n):
    desc = f"Length >= {n}"
    def maker(prev):
        return (lambda p: len(p) >= n, desc, lambda p, prev: f"Make the password at least {n} characters.")
    return maker

def length_at_most_factory(n):
    desc = f"Length <= {n}"
    def maker(prev):
        return (lambda p: len(p) <= n, desc, lambda p, prev: f"Shorten to {n} or fewer characters.")
    return maker

def contains_char_factory(chars, text=None):
    desc = text or f"Must contain one of: {chars}"
    def maker(prev):
        return (lambda p: any(c in p for c in chars), desc, lambda p, prev: f"Include one of: {chars}")
    return maker

def contains_digit_sum_mod_factory(mod, target=0):
    desc = f"Sum(digits) % {mod} == {target}"
    def maker(prev):
        def check(p):
            s = sum(int(c) for c in p if c.isdigit())
            return (s % mod) == target
        return (check, desc, lambda p, prev: f"Adjust digits so sum%{mod}=={target}. Current sum {sum(int(c) for c in p if c.isdigit())}.")
    return maker

def contains_prime_digit_factory():
    desc = "Has prime digit (2,3,5,7)"
    def maker(prev):
        return (lambda p: any(c in "2357" for c in p), desc, lambda p, prev: "Try adding 2,3,5 or 7.")
    return maker

def contains_fib_digit_factory():
    desc = "Has Fibonacci digit (0,1,2,3,5,8)"
    def maker(prev):
        return (lambda p: any(c in "012358" for c in p), desc, lambda p, prev: "Try adding 0,1,2,3,5 or 8.")
    return maker

def ascii_sum_divisible_factory(n):
    desc = f"ASCII sum % {n} == 0"
    def maker(prev):
        def check(p):
            return sum(ord(c) for c in p) % n == 0
        return (check, desc, lambda p, prev: f"Adjust one character to change ASCII sum mod {n} (current {sum(ord(c) for c in p) % n}).")
    return maker

def contains_word_factory(word):
    desc = f"Contains '{word}'"
    def maker(prev):
        return (lambda p: word.lower() in p.lower(), desc, lambda p, prev: f"Include '{word}'.")
    return maker

def no_word_factory(word):
    desc = f"Does NOT contain '{word}'"
    def maker(prev):
        return (lambda p: word.lower() not in p.lower(), desc, lambda p, prev: f"Remove '{word}' if present.")
    return maker

def ends_with_factory(suffix):
    desc = f"Ends with '{suffix}'"
    def maker(prev):
        return (lambda p: p.lower().endswith(suffix), desc, lambda p, prev: f"Make it end with '{suffix}'.")
    return maker

def starts_with_factory(prefix):
    desc = f"Starts with '{prefix}'"
    def maker(prev):
        return (lambda p: p.lower().startswith(prefix), desc, lambda p, prev: f"Start with '{prefix}'.")
    return maker

def no_letter_factory(letter):
    desc = f"No letter '{letter}'"
    def maker(prev):
        return (lambda p: letter.lower() not in p.lower(), desc, lambda p, prev: f"Remove '{letter}'.")
    return maker

def contains_letter_factory(letter):
    desc = f"Contains letter '{letter}'"
    def maker(prev):
        return (lambda p: letter.lower() in p.lower(), desc, lambda p, prev: f"Include '{letter}'.")
    return maker

def must_be_palindrome_factory():
    desc = "Be palindrome"
    def maker(prev):
        return (lambda p: p == p[::-1], desc, lambda p, prev: "Make it read the same forwards and backwards.")
    return maker

def must_not_be_palindrome_factory():
    desc = "NOT palindrome"
    def maker(prev):
        return (lambda p: p != p[::-1], desc, lambda p, prev: "Ensure p != reverse(p).")
    return maker

# prev-dependent factories
def contain_prev_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Contain previous (ignored)", lambda p, prev: "No previous password yet.")
        return (lambda p: prev in p, f"Contain previous '{prev}'", lambda p, prev: f"Insert '{prev}'.")
    return maker

def not_contain_prev_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Not contain previous (ignored)", lambda p, prev: "No previous password yet.")
        return (lambda p: prev not in p, f"Must NOT contain previous '{prev}'", lambda p, prev: f"Remove '{prev}'.")
    return maker

def contain_prev_last_char_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Contain prev last char (ignored)", lambda p, prev: "No previous password yet.")
        ch = prev[-1]
        return (lambda p: ch in p, f"Contain previous last char '{ch}'", lambda p, prev: f"Include '{ch}'.")
    return maker

def differ_from_prev_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Differ from previous (ignored)", lambda p, prev: "No previous password yet.")
        return (lambda p: p != prev, f"Different from previous '{prev}'", lambda p, prev: "Change at least one character.")
    return maker

def longer_than_prev_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Longer than previous (ignored)", lambda p, prev: "No previous password yet.")
        n = len(prev)
        return (lambda p: len(p) > n, f"Longer than previous length {n}", lambda p, prev: f"Make length > {n}.")
    return maker

def shorter_than_prev_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Shorter than previous (ignored)", lambda p, prev: "No previous password yet.")
        n = len(prev)
        return (lambda p: len(p) < n, f"Shorter than previous length {n}", lambda p, prev: f"Make length < {n}.")
    return maker

def contain_prev_reversed_factory():
    def maker(prev):
        if not prev:
            return (lambda p: True, "Contain prev reversed (ignored)", lambda p, prev: "No previous password yet.")
        rev = prev[::-1]
        return (lambda p: rev in p, f"Contain previous reversed '{rev}'", lambda p, prev: f"Include '{rev}'.")
    return maker

def alternating_factory():
    desc = "Alternate letters/digits"
    def maker(prev):
        def check(p):
            if len(p) < 2: return True
            for i in range(1, len(p)):
                if p[i].isalpha() == p[i-1].isalpha():
                    return False
            return True
        return (check, desc, lambda p, prev: "Try pattern a1b2a1.")
    return maker

def no_repeating_factory():
    desc = "Unique characters >= half length"
    def maker(prev):
        def check(p):
            if len(p) == 0: return False
            return len(set(p)) >= max(1, len(p)//2)
        return (check, desc, lambda p, prev: "Make characters more unique.")
    return maker

def require_upper_lower_factory():
    desc = "Contains upper AND lower"
    def maker(prev):
        return (lambda p: any(c.isupper() for c in p) and any(c.islower() for c in p), desc, lambda p, prev: "Add uppercase and lowercase letters.")
    return maker

def only_letters_factory():
    desc = "Only letters"
    def maker(prev):
        return (lambda p: all(c.isalpha() for c in p) and len(p)>0, desc, lambda p, prev: "Remove digits and special chars.")
    return maker

def only_digits_factory():
    desc = "Only digits"
    def maker(prev):
        return (lambda p: all(c.isdigit() for c in p) and len(p)>0, desc, lambda p, prev: "Use only digits.")
    return maker

def contains_month_factory():
    desc = "Contains a month name"
    def maker(prev):
        return (lambda p: any(m in p.lower() for m in MONTHS), desc, lambda p, prev: "Insert a month like 'may' or 'december'.")
    return maker

def contains_emoji_factory():
    desc = "Contains an emoji"
    def maker(prev):
        return (lambda p: any(c in EMOJIS for c in p), desc, lambda p, prev: f"Include an emoji such as {EMOJIS[:4]}.")
    return maker

def no_specials_factory():
    desc = "No special characters"
    def maker(prev):
        return (lambda p: all(c not in SPECIALS for c in p), desc, lambda p, prev: "Remove special characters like !@#$.")
    return maker

def require_special_factory():
    desc = "Requires a special character"
    def maker(prev):
        return (lambda p: any(c in SPECIALS for c in p), desc, lambda p, prev: f"Add a special character like {SPECIALS[:4]}.")
    return maker

def vowel_consonant_ratio_factory(min_vowels, max_consonants):
    desc = f"At least {min_vowels} vowels and at most {max_consonants} consonants"
    def maker(prev):
        def check(p):
            return count_vowels(p) >= min_vowels and count_consonants(p) <= max_consonants
        return (check, desc, lambda p, prev: f"Vowels: {count_vowels(p)}, Consonants: {count_consonants(p)}.")
    return maker

# ---------------------
# Deterministic FACTORIES list (100 items)
# ---------------------
FACTORIES = []
FACTORIES.extend([
    length_at_least_factory(6),
    length_at_least_factory(8),
    length_at_least_factory(10),
    length_at_least_factory(12),
    length_at_least_factory(15),
    length_at_most_factory(40),
    contains_char_factory(string.digits, "Has a digit"),
    contains_prime_digit_factory(),
    contains_fib_digit_factory(),
    contains_digit_sum_mod_factory(7),
    contains_digit_sum_mod_factory(3),
    ascii_sum_divisible_factory(13),
    ascii_sum_divisible_factory(17),
    contains_emoji_factory(),
    contains_month_factory(),
    contains_word_factory("code"),
    contains_word_factory("game"),
    contains_word_factory("win"),
    contains_word_factory("play"),
    contains_word_factory("fun"),
    no_word_factory("password"),
    no_word_factory("secret"),
    no_word_factory("fail"),
    require_special_factory(),
    no_specials_factory(),
    contains_char_factory(SPECIALS, "Has a special char"),
    require_upper_lower_factory(),
    only_letters_factory(),
    only_digits_factory(),
    must_be_palindrome_factory(),
    must_not_be_palindrome_factory(),
    contain_prev_factory(),
    not_contain_prev_factory(),
    contain_prev_last_char_factory(),
    differ_from_prev_factory(),
    longer_than_prev_factory(),
    shorter_than_prev_factory(),
    contain_prev_reversed_factory(),
    alternating_factory(),
    no_repeating_factory(),
    vowel_consonant_ratio_factory(2, 6),
    contains_char_factory("AEIOU", "Has uppercase vowel"),
    contains_char_factory("aeiou", "Has lowercase vowel"),
    contains_char_factory("BCDFGHJKLMNPQRSTVWXYZ", "Has uppercase consonant"),
    contains_char_factory("bcdfghjklmnpqrstvwxyz", "Has lowercase consonant"),
    contains_char_factory("0123456789", "Has a digit (explicit)"),
    ascii_sum_divisible_factory(11),
    ascii_sum_divisible_factory(19),
    contains_char_factory("01234", "Has small digit (0-4)"),
    contains_char_factory("56789", "Has large digit (5-9)"),
    starts_with_factory("py"),
    starts_with_factory("s"),
    ends_with_factory("ing"),
    ends_with_factory("ed"),
    ends_with_factory("er"),
    ends_with_factory("ly"),
    no_letter_factory("a"),
    no_letter_factory("z"),
    no_letter_factory("q"),
    contains_letter_factory("e"),
    contains_letter_factory("o"),
    contains_letter_factory("t"),
    contains_letter_factory("r"),
    contains_letter_factory("n"),
    contains_letter_factory("s"),
    contains_letter_factory("l"),
    contains_letter_factory("p"),
    vowel_consonant_ratio_factory(3, 7),
    contains_emoji_factory(),
    require_special_factory(),
    contains_char_factory("!@#", "Has one of !,@,#"),
    contains_char_factory("$%^", "Has one of $,% ,^"),
    contains_char_factory("-_+", "Has one of -,_ ,+"),
    contains_word_factory("hard"),
    no_word_factory("easy"),
    contains_word_factory("challenge"),
    contains_word_factory("neal"),
    contains_word_factory("rule"),
    contains_word_factory("level"),
    ascii_sum_divisible_factory(23),
    ascii_sum_divisible_factory(29),
    contains_digit_sum_mod_factory(5),
    contains_digit_sum_mod_factory(9),
    contains_digit_sum_mod_factory(11),
    contains_char_factory("💡🔥", "Has one of these emojis")
])
# pad to 100 deterministically
i = 0
while len(FACTORIES) < 100:
    FACTORIES.append(length_at_least_factory(6 + (i % 10)))
    i += 1
FACTORIES = FACTORIES[:100]

# ---------------------
# Build active rules for level (capture prev)
# ---------------------
def build_active_rules(prev, level):
    makers = FACTORIES[:level]
    active = [maker(prev) for maker in makers]
    return active  # list of (check_fn, desc, hint_fn)

def check_all(password, active_rules, prev):
    failed = []
    for check_fn, desc, hint_fn in active_rules:
        try:
            ok = bool(check_fn(password))
        except Exception:
            ok = False
        if not ok:
            failed.append((desc, hint_fn(password, prev)))
    return (len(failed) == 0, failed)

# ---------------------
# Interactive edit loop
# ---------------------
def play():
    random.seed(0)
    prev = ""  # previous password (the one you keep editing)
    print("\nNEAL-LIKE PASSWORD GAME — EDIT-IN-PLACE")
    print("Type a password to satisfy level 1. Each time active rules pass, next rule unlocks.")
    print("Commands: hint / show / quit\n")

    for level in range(1, 101):
        active = build_active_rules(prev, level)
        print("\n" + "="*60)
        print(f"LEVEL {level} — {len(active)} active rule(s).")
        # show active rules
        for idx, (_, desc, _) in enumerate(active, 1):
            print(f"{idx:3d}. {desc}")

        # if prev empty, force an initial entry
        candidate = prev
        first_prompt = True
        while True:
            if candidate:
                print(f"\nCurrent password (editing): '{candidate}'")
                prompt = "Edit password (type full password), or press Enter to keep current: "
            else:
                prompt = "Type initial password to begin: "
            entry = input(prompt).strip()
            if entry.lower() == "quit":
                print("Exiting game.")
                return
            if entry.lower() == "show":
                print("\nActive rules:")
                for idx, (_, desc, _) in enumerate(active, 1):
                    print(f"{idx:3d}. {desc}")
                continue
            if entry.lower() == "hint":
                # use candidate if present else prev or a sample
                trial = candidate or prev or "Test123!"
                ok, fails = check_all(trial, active, prev)
                if fails:
                    desc, hint = fails[0]
                    print(f"HINT for first failing rule: {desc}\n -> {hint}")
                else:
                    print("Current password passes all active rules. Press Enter to keep or edit to change.")
                continue

            # if user pressed Enter to keep current and candidate exists
            if entry == "" and candidate:
                trial = candidate
            else:
                trial = entry

            ok, fails = check_all(trial, active, prev)
            if ok:
                prev = trial  # update the password you will continue editing next level
                print(f"✅ Level {level} cleared. Password locked for this level: '{prev}'")
                break
            else:
                print("❌ Failed rules:")
                for idx, (desc, hint) in enumerate(fails, 1):
                    print(f" {idx}. {desc}")
                # set candidate to trial so user can edit it next loop
                candidate = trial
                # next loop allows editing of candidate

    print("\n🎉 You completed all 100 levels. Nicely done.")

if __name__ == "__main__":
    play()
