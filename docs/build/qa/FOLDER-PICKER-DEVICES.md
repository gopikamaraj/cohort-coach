# Folder picker: device checklist

Enter check adds many sheet pictures at once with **Select a folder of pictures** (the `webkitdirectory`
file input, found by feature detection). Where a browser cannot choose a folder the button reads
**Choose pictures** and the teacher picks many pictures from the gallery. Desktop Chromium is proved by
automated tests (`e2e/enter-check.spec.ts`); the phones below need a person with the device.

## How to test one device

1. Open the hosted app on the device (or the installed web app). Use the standard test paper and the
   folder `demo/test-sheets/` (or the Drive copy). Set the class size to 10.
2. Tap the button under **Add the sheets** and note its label (Select a folder of pictures or Choose pictures).
3. Choose the folder (or all ten pictures). Note whether the picker offered a folder or only pictures.
4. Watch the summary line. Record how many pictures arrived (expect 10) and how many matched a roll number
   by file name. **Mobile Safari can scramble file names**, so a low match count is information, not a failure:
   the header reading or the roll chooser takes over.
5. Start a stopwatch when you choose the files and stop it when **Reading 10 of 10** goes away. Record the seconds
   for 10 pictures (multiply by two for 20).
6. Put the phone in airplane mode and check that both buttons are disabled with the reason, and that typing works.

## Results (to be filled in by the team)

| Device and browser | Version | Installed app or browser | Button label | Picker offers | All 10 arrive | File names kept | Seconds for 10 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Chrome on Android | | browser | | | | | | |
| Chrome on Android | | installed | | | | | | |
| Samsung Internet | | browser | | | | | | |
| Safari on iOS | | browser | | | | | | |
| Safari on iOS | | home-screen app | | | | | | |
| Chrome, desktop | | browser | | | | | | |
| Edge, desktop | | browser | | | | | | |
| Firefox, desktop | | browser | | | | | | |
| Safari, desktop | | browser | | | | | | |

## What the sources say (confirm on the day)

From browser compatibility data: `webkitdirectory` works in desktop Chrome, Edge, Firefox and Safari and in
recent Chrome for Android. In Safari on iOS it works only from version 18.4. Samsung Internet, Opera Mini
and UC Browser do not support it, and some mobile pickers cannot choose a folder at all. The fallback
(**Choose pictures**) is therefore part of the design, not an error path.
