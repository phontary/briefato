<!--
asset: briefato-brain/standards/index
provenance: Nutzer-Methode Schreibdienst-Profil — Auswahlindex über die Abteilungsstandards
  für Operationsberichte (skills/medizin/operationsbericht/SKILL.md + references/).
scope: Trigger-Auswahl der Standards für den Dokumenttyp operationsbericht.
-->

# Standards-Index — Abteilungsstandards Operationsbericht

Der Dokumenttyp `operationsbericht` erhält immer genau EINEN Abteilungsstandard als verbindliches
Gerüst (unabhängig von der optionalen Referenz-Anreicherung). Die Auswahl erfolgt über die
Trigger-Begriffe: Das Diktat wird umlautgefaltet und kleingeschrieben; es gewinnt der erste Treffer
nach aufsteigender Reihenfolge. Trigger mit bis zu fünf Zeichen matchen nur als ganzes Wort
(Wortgrenze), längere Trigger auch als Wortbestandteil (deutsche Komposita). Greift kein Trigger,
gilt der generische Fallback.

| Reihenfolge | Datei | Trigger-Begriffe |
|:--:|---|---|
| 1 | che-laparoskopisch.md | cholezystektomie, cholecystektomie, che, gallenblase, gallensteine, cholezystolithiasis, cholelithiasis, calot |
| 2 | narbenhernie-sublay.md | narbenhernie, narbenhernien, sublay, ipom, netzplastik, bauchwandhernie, medianlaparotomie |
| 99 | op-standardschritte.md | * |
