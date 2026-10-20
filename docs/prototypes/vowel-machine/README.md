# Vowel Machine v0.3.1 reference archive

## Identity and provenance

The local prototype directory and its `vowel-machine-v0.3.1.zip` identify this as **v0.3.1**. The package's local timestamp is 2026-10-19; it is an approximate local packaging date, not verified authorship or original creation time. Every member of the supplied ZIP matched the corresponding loose file byte for byte before archiving. The loose `index.html` and `app.js` are the reference executable copy. `index-v0.2.html` is an older Explore-only baseline; `reference-vowel-forge.html` is an exact copy of the Forge HTML. A separate v0.3 ZIP existed locally but was not selected as the v0.3.1 reference.

The supplied v0.3.1 ZIP and `DESIGN_NOTES.md` contained one personal absolute path. The archived note changes **only that path** to a relative link. The archived `vowel-machine-v0.3.1.zip` was rebuilt from the archived files to remove that path. It is a **redacted reproduction package, not the original ZIP bytes**. The original note SHA-256 was `983FD9D5D8C93B0E44256B13F276A95E39034BA764B2AB7CCCA1A83ACE040F83`; the original ZIP SHA-256 was `DA5C053A354DA3B17CC1E840AB90B40DBFFD041CDF89CE6F78B41F9016FE2D19`. Those originals were deliberately not committed. All executable files, images, original README, beginner protocol, and verifier are byte-identical to their selected originals. The original v0.3 ZIP and generated screenshots are not needed to run v0.3.1 and are not archived.

| File under `original/` | Role | SHA-256 |
| --- | --- | --- |
| `index.html` | Entry page and styles | `18669A05B3824648258F1BCB12C0B48334944071F56AA2C6F88B0E34387D9EC3` |
| `app.js` | Interaction and assessment logic | `6D42B20998C41491380F65248B461020D1D52DA56A72E30A023DDB4AD3ECEA44` |
| `assets/jeong_hello.png` | Guide image | `A2AC16ADFED47658F44876CBA663D776CB74406A5DB9142095A948BD377039D3` |
| `assets/jeong_curious.png` | Guide image | `A14B7F0727C4A7F8CEDE9E05EA00CD19DB48171A3B626EDB7A62E48EBFC9F0F5` |
| `assets/jeong_delighted.png` | Guide image | `3B061E87E647FA7FBE3F2073007B4A10C9703411BD1D118083CC75C6F1EDAA8C` |
| `README.md` | Original run instructions | `6969F898764659FE865FF0AB369932223574022441F243395FE0B94CEDDFF0E9` |
| `DESIGN_NOTES.md` | Design rationale; one path redacted | `BA3350627D2E907FD08DD7363ED50C212DB98FB2CD821E3F617F87E6A2084D0B` |
| `BEGINNER_TEST.md` | Proposed novice observation protocol | `8919A7C3FDB4CB77FFC1CC1423AA89A3EAAE973C2440BA69002915220C808124` |
| `verify_vowel_machine.py` | Original Playwright regression script | `0984701E4E41116635BBA2241C2CDF45D025B4B35066E60EE3155E3D9DAF29B5` |
| `index-v0.2.html` | Earlier Explore baseline | `1782B33ADDF20684F5CB192C510C697B33FB71AD3374F1638B779B0F8D0BDE0E` |
| `reference-vowel-forge.html` | Byte-identical Forge reference | `B4FE121E23352E65C6B906B014D99BCC97155CDB662517B88991193F52EBD821` |
| `vowel-machine-v0.3.1.zip` | Redacted reproduction ZIP | `6941AD212D3C4344D2BA7D24F195D0B9BAE840D7AD37425EA6790B98C2E230D3` |

Git attributes disable text conversion under `original/`. The file hashes above describe checked-out bytes on any platform that honors the repository attributes.

## Implemented behavior

Both tabs work with ㅏ, ㅓ, ㅗ, and ㅜ and retain separate in-memory state. **Move strokes** slides a short joint across a line and uses Turn base to change the axis; side buttons provide a non-drag route. **Three keys** combines two taps of ㆍ, ㅡ, and ㅣ. Explore reveals vowel shapes and unlocks a ㄴ syllable row (나, 너, 노, 누). Prove prompts with approximate `a`, `eo`, `o`, and `u` cues while concealing the target glyph and row; Check submits a construction. Wrong submissions keep the challenge and describe the differing component. After two wrong submissions a clue becomes available; later completion is marked assisted. A four-item, non-manipulable multiple-choice vowel recognition check follows each method. The in-memory report records order, attempts, first unaided success, clue use, and errors. There is no persistent save, audio, grading beyond this session, or independent syllable-reading assessment.

## Relationship to current design

The visual rail illustrates side and above/below contrast; its non-drag controls and hidden-target Check/feedback loop are useful research references. The rail's rotation is superseded as the primary instructional mechanic by fixed-base stem-and-stroke construction. Three-key grammar remains a later input-transfer experiment. The glowing ㄴ row can inform a later syllable-combination workshop, but it does not teach or prove the separate act of combining completed jamo. The immediate recognition check is useful as limited evidence, not mastery or durable retention. Test novices on sound-cue comprehension, cue leakage, position prediction, and accessibility. The rail is a shape model, not handwriting stroke-order instruction. The historical heaven/earth/human explanation in the original notes is a sourced design context; the rail, exact key rule, grid, and character dialogue are inventions.

## Reproduction and verification

Open [original/index.html](original/index.html) directly in a modern browser, or serve `original/` with a static HTTP server. Keep `app.js` and `assets/` beside it. The page is designed for offline use; there is no backend or account. Python Playwright and its Chromium browser are required only for `verify_vowel_machine.py`, which also writes three PNG screenshots into its working directory; run it from a disposable copy if you want to keep the archive clean. The archived reproduction ZIP contains the same runnable files and redacted note, and the verifier's ZIP member comparison can use it.

Archive verification: Chromium ran the original verifier from a disposable copy at 390×844 and 320×568. Explore, Prove, transfer, wrong-answer retry, assistance, separate mode state, replay, assets, short-screen layout, drag, keyboard focus, reduced motion, rail shortcut cases, and reproduction-ZIP member parity passed. **The unmodified historical verifier does not finish:** its keys-first case closes its browser context too early, omits a wrong-answer setup, expects the second-method transfer order for the first method, and expects the other method to be complete when it remains in Prove. Those test-only mistakes were corrected in the disposable copy to complete the run; the archived verifier and application were not edited. This is evidence for the exercised browser paths, not a claim that the archived test script passes unchanged. Physical-phone behavior, screen-reader use, beginner learning, and delayed retention remain unverified.
