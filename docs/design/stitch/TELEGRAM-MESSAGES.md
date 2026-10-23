# Telegram messages (not a Stitch screen)

Telegram is the primary teacher channel. These are the teacher's messages as text mockups, so the web screens and the bot say the same things. The bot only renders steps from the flow engine; the words come from `strings/{en,hi,ta}.json`. Counts only, never percentages; no child names; one question per message; every message is short enough to read aloud.

Button labels in Hindi and Tamil below are drafts and **need Shivani** before they are shown to a teacher.

Format: a line starting with `Bot:` is a message; lines in square brackets are inline buttons (one per row); `[voice note]` is an audio message.

## 1. Lesson voice note with reply buttons

```text
Bot: [voice note, 4:40, about 0.6 MB]
     Lesson 3: Open one bundle
     Checked. Reviewed by the programme team.
     [Play model run]  [Practice with the children]
```

After she has played it (Telegram cannot confirm a play, so the bot never says "listened"), two taps:

```text
Bot: Tried it in class?
     [Yes]
     [Not yet]

Bot (after Yes): How did it go?
     [Worked]
     [Partly]
     [Didn't work]

Bot: Tell me in a 1-minute voice note: what did you try, and what did the children say?
     (Optional. Send a voice note, or ignore this.)
```

One-tap variant named in the design brief (one message, three buttons):

```text
Bot: Lesson 3. Did you try it in class?
     [Tried it]
     [Partly]
     [Not yet]
```

The repo currently ships the two-tap version (`docs/build/BUILD_PROMPTS.md` P10 step 3). The one-tap variant needs a decision from Gopi before it replaces it, because it merges "tried it" with "how did it go". See the report.

Hindi and Tamil button labels (need Shivani):

| English | Hindi (draft) | Tamil (draft) |
| --- | --- | --- |
| Yes | हाँ | ஆம் |
| Not yet | अभी नहीं | இன்னும் இல்லை |
| Worked | काम किया | வேலை செய்தது |
| Partly | कुछ हद तक | ஓரளவு |
| Didn't work | काम नहीं किया | வேலை செய்யவில்லை |
| Tried it | आज़माया | முயன்றேன் |

After her voice note, one next step comes back, never a score:

```text
Bot: Thank you. You said children opened a bundle by themselves.
     Next step: ask them to say each step aloud.
     Checked.
```

## 2. Silence nudge

A calm message after a week with no replies. It never says failed, ignored, late or behind; no response reads as no response.

```text
Bot: Lesson 4 is ready when you are. It takes 5 minutes.
     [Play lesson 4]  [Later]
```

Hindi (draft, needs Shivani): पाठ 4 तैयार है, जब आप चाहें। इसमें 5 मिनट लगते हैं।
Tamil (draft, needs Shivani): பாடம் 4 தயாராக உள்ளது, நீங்கள் விரும்பும்போது. இதற்கு 5 நிமிடம் ஆகும்.

## 3. Termly check reminder

```text
Bot: It is time for this term's check. Enter the answers of your Grade 3 class, or send a photo of each sheet.
     [Enter the check]  [Send photos]  [Remind me later]
```

Hindi (draft, needs Shivani): इस सत्र की जाँच का समय हो गया है। अपनी तीसरी कक्षा के जवाब दर्ज करें, या हर कॉपी की फ़ोटो भेजें।
Tamil (draft, needs Shivani): இந்தப் பருவத்தின் சோதனைக்கான நேரம் இது. உங்கள் மூன்றாம் வகுப்பின் பதில்களைப் பதிவு செய்யுங்கள், அல்லது ஒவ்வொரு தாளின் புகைப்படத்தையும் அனுப்புங்கள்.

## 4. Photo-capture prompts

Sheets carry no name or roll number; she sends them in roll order, and only her phone knows which is which.

```text
Bot: Send the answer sheets in roll order, one photo each. If a child was absent, send [Skip this roll number].
     [Skip this roll number]

Bot: Sheet 1 received. Reading it now.
Bot: Sheet 1 read. 1 box needs your check: question 4. What does the child's answer say?
     [Type the number]  [Can't read]  [Leave blank]

Bot: Sheet 2 received.
Bot: I could not read sheet 3. Please send it again, flat and in good light.
Bot: Photos deleted from this chat once read.   (If the bot cannot delete them, it asks her to.)
Bot: 28 sheets read. 3 boxes you confirmed. Your class result is ready.
     [See what my class gets wrong]
```

The bot never repeats a child's answers in a message and never asks for a name.

Hindi and Tamil button labels (need Shivani):

| English | Hindi (draft) | Tamil (draft) |
| --- | --- | --- |
| Skip this roll number | यह रोल नंबर छोड़ें | இந்த வரிசை எண்ணைத் தவிர்க்கவும் |
| Type the number | संख्या लिखें | எண்ணைத் தட்டச்சு செய்யுங்கள் |
| Can't read | पढ़ा नहीं जा सकता | படிக்க முடியவில்லை |
| Leave blank | खाली छोड़ें | காலியாக விடுங்கள் |
| See what my class gets wrong | मेरी कक्षा कहाँ गलती करती है | என் வகுப்பு எங்கே தவறு செய்கிறது |

## 5. Link into the web app

Some things only work in the web app: the Practice Class, the check on a big screen, the cohort page for mentors.

```text
Bot: Rehearse with five pretend children before you try it in class. It opens in the web app.
     [Open the Practice Class]   (a signed link that carries only the language and the error, no person)

Bot: You can use the bot and the web app together. Your code is KX7M2R9T (valid 15 minutes, works once).
     Enter it in the web app under My profile.
     [Open the web app]
```

Hindi and Tamil button labels (need Shivani):

| English | Hindi (draft) | Tamil (draft) |
| --- | --- | --- |
| Open the Practice Class | प्रैक्टिस क्लास खोलें | பயிற்சி வகுப்பைத் திற |
| Open the web app | वेब ऐप खोलें | வலை செயலியைத் திற |
| Play lesson 4 | पाठ 4 सुनें | பாடம் 4 ஐ இயக்கு |
| Later | बाद में | பிறகு |
| Remind me later | मुझे बाद में याद दिलाएँ | பிறகு நினைவூட்டு |

## Rules for every message

- Counts, never percentages. No child names, no roll numbers in text.
- Every lesson carries the badge line (Checked, Reviewed) in her language.
- Never "listened", "watched", "failed", "ignored" or "behind".
- Buttons are short, one per row, and at least one word long in every language; labels may grow 30 percent in Hindi and Tamil.
- Her time stays within the 20-minute weekly cap; the bot sends at most one lesson and one nudge a week.
