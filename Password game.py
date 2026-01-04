# streamlit_password_game_fixed.py
import streamlit as st
import string

st.set_page_config(page_title="Password Game", layout="wide")

# ----------------------
# Simple rules for demo
# ----------------------
SPECIALS = "!@#$%^&*()-_+="
MONTHS = ["january","february","march","april","may","june","july","august",
          "september","october","november","december"]

def count_vowels(s):
    return sum(1 for c in s if c.lower() in "aeiou")

def alternating_letters_numbers(p):
    for i in range(1, len(p)):
        if p[i-1].isalpha() == p[i].isalpha():
            return False
    return True

RULES = [
    ("Length ≥ 6", lambda p: len(p) >= 6),
    ("Contains a digit", lambda p: any(c.isdigit() for c in p)),
    ("Contains a special character", lambda p: any(c in SPECIALS for c in p)),
    ("Contains a month name", lambda p: any(m in p.lower() for m in MONTHS)),
    ("Alternating letters & digits", alternating_letters_numbers),
    ("At least 2 vowels", lambda p: count_vowels(p) >= 2),
]

# ----------------------
# Session state
# ----------------------
if "level" not in st.session_state:
    st.session_state.level = 1
if "password" not in st.session_state:
    st.session_state.password = ""
if "message" not in st.session_state:
    st.session_state.message = ""

st.title("Password Game — Simplified Neal-like Demo")

pwd_input = st.text_input("Password:", value=st.session_state.password)

if st.button("Submit"):
    active_rules = RULES[:st.session_state.level]
    failed = []
    for desc, fn in active_rules:
        try:
            if not fn(pwd_input):
                failed.append(desc)
        except:
            failed.append(desc)
    if failed:
        st.session_state.message = f"Failed {len(failed)} rule(s): {', '.join(failed)}"
    else:
        st.session_state.password = pwd_input
        st.session_state.level += 1
        st.session_state.message = f"Level cleared! Password locked: '{pwd_input}'"
        if st.session_state.level > len(RULES):
            st.success("🎉 All levels cleared!")

st.write(st.session_state.message)
st.write(f"Current level: {st.session_state.level}/{len(RULES)}")

st.subheader("Active rules")
for idx, (desc, _) in enumerate(RULES[:st.session_state.level], 1):
    st.write(f"{idx}. {desc}")
