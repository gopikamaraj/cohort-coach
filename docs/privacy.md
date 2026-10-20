# Privacy and DPDP (draft, 2026-10-20)

**This is the team's working document, not legal advice.** India's Digital Personal Data Protection Act, 2023 (DPDP) applies to personal data of teachers and, if we ever hold it, of children. The programme's legal reviewer must confirm every row marked *to confirm* before real teachers or real children's data are involved. The in-app notice (`/#/privacy`, three languages) says the same things in plain words.

## 1. Data map

| Data item | Purpose | Where stored | Retention | Who sees it | Consent / basis |
| --- | --- | --- | --- | --- | --- |
| Each child's answers (typed or read from a photo) | Find which mistakes the class makes | **Only the teacher's phone** (IndexedDB) | Until she deletes the class or erases her data | Her only | Not sent anywhere; no consent needed to keep it on her own phone |
| Sheet photo | Read the answers | Server memory for one call, then dropped; never on disk or in logs; not kept on the phone | Seconds | Nobody | Used only when she takes a photo; AI service (Claude) processes it |
| Class counts (how many children show each error) | Group teachers by shared mistakes | Server, under a random class id (no name, school or teacher) | Until the teacher erases the class (`DELETE /api/classes/{id}`) | Programme (aggregates; fewer than 5 classes hidden) | Consent `counts` (off by default) |
| Practice Class words (typed or spoken) | The pretend children answer | AI services for the reply (Claude, Sarvam); the record stays on her phone; audit rows hold metadata only | Not kept on our servers | Her only | Consent `practice_ai` (asked before first use) |
| Her voice | Turn speech into text | Sarvam, then dropped | Not stored | Nobody | Same consent |
| Rehearsal recordings, her impact tag | Replay and improve | Her phone | Until she deletes | Her only | `share_rehearsal` only if she chooses to share (no sharing endpoint exists yet) |
| Classroom observation (choices only) | Tune the simulator | Server table `sim_observations`, no id | While the product is improved | Admin | Consent `feedback` |
| App, content and card feedback (rating, up to 500 characters) | Improve the app | Server table `feedback`, no name, class or device id; text refused if it holds a phone number, email or ID number | While the product is improved | Admin | Consent `feedback` |
| Consent records | Prove what she agreed to | Her phone, and the server (`consents`) under a random device id | While the programme runs | Admin | Legal obligation to keep proof (*to confirm*) |
| Data used (bytes) | Show her what the app costs | Her phone only | Until she clears it | Her only | Not sent |

## 2. DPDP principles and where each is met

| Requirement | How |
| --- | --- |
| Notice before consent, in clear language, in her language | `/#/privacy` in en, hi, ta; shown on first open (Home prompt) and before AI is first used |
| Free, specific, informed, unambiguous consent; withdrawable as easily as given | Four separate switches in My profile, all **off by default**; "Withdraw all" is one tap; each change is recorded with a version and time |
| Purpose limitation and minimisation | Per-child answers never leave the phone; the server holds counts and anonymous feedback only |
| Accuracy and correction | The check can be edited at any time; history is readable |
| Access | "What I entered" (screen) and "Save a backup" (a full file, optionally sealed with a passphrase) |
| Erasure | "Erase everything" clears every table on the phone and asks the server to erase the class counts; deleting one class does the same for that class. Feedback and observations carry no identifier, so they cannot be traced back and are not erasable by her (stated in the notice) |
| Storage limitation | Photos: seconds. Rehearsal text: not on our servers. Counts and feedback: while the programme runs |
| Security safeguards | HTTPS in production; per-class random ids; no per-child data on the server; backup files can be encrypted (AES-GCM, key from PBKDF2, 600,000 iterations) and a restored file is checked for shape, size and ids; admin endpoints are closed unless `ADMIN_KEY` is set (or `ADMIN_OPEN=1` on purpose for local dev and the judge demo) and the key is compared in constant time; CORS limited to the PWA's own origin; no secrets in git |
| Children's data (verifiable parental consent, no tracking or targeted ads) | We hold no child's name, face, voice or roll number, and answers stay on the teacher's phone; because no child is identifiable to us we believe we hold no children's personal data (*to confirm with legal review*) |
| Data processors | Anthropic (Claude) and Sarvam AI process Practice Class text, speech and sheet photos only to answer her; our host stores counts and feedback. Contracts and cross-border transfer terms: *to confirm* |
| Grievance redressal | Contact shown in the notice: **placeholder** `TODO-HUMAN(Seema, Gopi)`: name, email, phone of the grievance officer, response time |
| Right to nominate | Described in the notice; the process (written request to the contact) is a placeholder |
| Breach notification | Process not written: `TODO-HUMAN(Gopi)` before real use |

## 3. What is not done

- The grievance contact and the nominee and breach processes are placeholders.
- No server-side access request (a teacher can only export from her phone), and no server-side deletion for feedback (it is anonymous by design).
- `ADMIN_KEY` is a shared key, not named admin accounts. With no key the admin endpoints are closed (503); `ADMIN_OPEN=1` opens them for local dev and the judge demo only, and must never be set on a public server.
- Withdrawing consent stops sending and drops queued feedback, but counts already sent stay on the server until she erases them. Consent records on the server are kept as proof and are not erased by "Erase everything"; the phone's own consent record, device id and settings are.
- If "Erase everything" runs offline the server's class counts are not erased (the class ids are gone from the phone); a pending-erase queue is not built.
- A teacher can still type a child's name into feedback text: the server only refuses phone numbers, emails and ID numbers. That is why the admin page must stay closed to the public.
- No named data fiduciary, no cross-border statement, no breach statement and no rate limit on feedback and consent posts yet.
- The fetch meter clones each API response that lacks a content-length to count it; on very low-end phones this doubles a reply's memory briefly.
- Consent for a teacher who is a minor, and the age gate, are not needed (teachers are adults) and are not built.
- Retention periods for server data are stated as "while the programme runs"; a number of days should be agreed.
- Data localisation and cross-border transfer (Claude and Sarvam endpoints) have not been reviewed.
- The pilot's roll-number pairing is covered in `CLAUDE.md` section 4 (local script, nothing leaves the machine).

## 4. Practical notes

- **Backup files hold children's answers.** The app says so next to the export button; sealing with a passphrase is optional, not forced.
- **Persistent storage** is requested so the browser does not clear the phone's data; a browser may decline, and the profile page says which it did.
- **Data used** is counted on the phone from the app's own calls and never sent.
- Uploads from the Practice Class voice turn may be spooled to a temporary file by the framework above 1 MB; the audio is the teacher's own and is deleted on close (see `docs/speech.md`).
