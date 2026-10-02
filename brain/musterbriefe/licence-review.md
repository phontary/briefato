# Lizenz-Review – Herkunft von Text und Quellen

Zweck: Musterbriefe identifizieren, deren Formulierungen ganz oder teilweise aus
kostenpflichtigen/urheberrechtlich geschützten Quellen (AMBOSS, DocCheck Flexikon,
MSD Manual, PubMed/Paper, AWMF/DGVS-Leitlinien) übernommen wirken.

Ergebnis: **4 von 152** Dateien mit Quellenangabe und/oder
Quellenmarkern → `licence_risk = "review"` im Manifest.

## Dateien mit `## Quellen` und/oder übernommen wirkender Prosa

| Datei | beobachtete Marker | Bewertung |
|---|---|---|
| `Coxarthrose_Exsikkose_Sturz.md` | AWMF, DocCheck, Flexikon, MSD Manual, S2k-Leitlinie | Explizite `## Quellen`-Liste (DocCheck Flexikon, MSD Manual, AWMF S2k Koxarthrose). |
| `Pangastritis.md` | AWMF, DocCheck, Flexikon, MSD Manual, PubMed, S2k-Leitlinie | `## Quellen` (DocCheck, MSD Manual Professional, AWMF S2k H. pylori 021-001, PubMed/Am J Gastroenterol 2002); sehr langer enzyklopädischer Text. |
| `Papillaere_Pankreatitis.md` | AWMF, DocCheck, Flexikon, MSD Manual, S3-Leitlinie | `## Quellen` (DocCheck, MSD Manual, AWMF/DGVS S3 Pankreatitis 021-003); Fließtext mit wörtlichen Leitlinien-Wiedergaben und Quellenkürzeln im Satz. |
| `Proktitis.md` | AWMF, DocCheck, Flexikon, MSD Manual, PMID, PubMed, S3-Leitlinie | `## Quellen` (DocCheck, MSD Manual, AWMF S3 Colitis ulcerosa, DGVS, PubMed PMID 2204103); zahlreiche Absätze mit Klammerverweisen `(DocCheck Flexikon)`/`(MSD Manual)` direkt im Text — stark nach Übernahme aussehend. |

Hinweis: In mehreren Briefen steht die Quellenangabe **im Fließtext in Klammern**
(z. B. „(DocCheck Flexikon)“, „(AWMF S3-Leitlinie …)“), nicht nur im `## Quellen`-Block.
Das ist ein starkes Indiz für (teil-)wörtliche Übernahme.

## Empfohlene Regel

> **Die Struktur eines Musterbriefs darf uns inspirieren, die lizenzierte Prosa nicht.**

1. Lizenzierten Text (AMBOSS/DocCheck/MSD/Paper/Leitlinien) **nicht wörtlich** in das
   ausgelieferte Produkt oder in Trainings-/Few-Shot-Beispiele übernehmen.
2. Ziel ist eine eigene, generische Arztbrief-Vorlage pro Indikation: medizinisch korrekt,
   aber in eigener Formulierung; Leitlinien nur als Fakten-Referenz, nicht als Satzspender.
3. Die 4 markierten Dateien vor Nutzung als Referenz **umschreiben** (paraphrasieren) und
   die Quellen-Klammern im Fließtext entfernen; `## Quellen` als reine Lese-Referenz behalten,
   nie in generierte Kundenbriefe übernehmen.
4. `licence_risk == "review"` im Manifest als Gate behandeln: erst nach Paraphrase-Freigabe
   in Retrieval/Few-Shot aufnehmen.
