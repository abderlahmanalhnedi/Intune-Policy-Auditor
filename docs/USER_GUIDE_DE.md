# Benutzerhandbuch (Deutsch)

## Intune einfach erklärt

Microsoft Intune verwaltet Einstellungen für Benutzer und Geräte. Eine **Richtlinie** beschreibt die beabsichtigte Konfiguration. Eine **Zuweisung** bestimmt, welche Gruppen, Benutzer oder Geräte sie erhalten sollen; Filter können die Zielmenge weiter eingrenzen. Ein JSON-Export beweist nicht, dass ein Gerät die Richtlinie erfolgreich angewendet hat. Mehrere Richtlinien können dieselbe Einstellung konfigurieren.

## Prüfung durchführen

Anwendung starten, **Neue Prüfung** wählen, JSON/ZIP hochladen oder die Demo öffnen und die erkannten Richtlinien-/Einstellungszahlen prüfen. Danach ein aktives Knowledge Pack oder ausdrücklich die eingeschränkte Analyse wählen. Akzeptierte Abweichungen, validierte organisatorische Anforderungen sowie Ziel-/Pilotkontext sind optional. Anforderungen werden nachvollziehbar gespeichert, erzeugen derzeit aber keine Befunde. Im Offline-Modus bleiben Dateien lokal; Rohdaten werden nicht gespeichert.

Das Dashboard zeigt die Gesamtentscheidung. **Richtlinien** erklärt Inhalte und Zuweisungen. **Ergebnisse** zeigt Fund, aktuellen/ausgewählten Wert, mögliche Wirkung, nächste Schritte, Pilot, Rollback, Sicherheit, Quelle und Entscheidungsspur. Der Filter **Nicht bewertbar** ergänzt vorhandene/fehlende Evidenz und einen Klärungsvorschlag. **Konflikte** trennt Duplikate von bestätigten/wahrscheinlichen/möglichen Überschneidungen. **Knowledge Packs** zeigt Version, Hash, Alter und Herkunft. **Berichte** bietet neun Formate.

**Nicht bewertbar** bedeutet: Ein notwendiger Beleg fehlt. Das ist weder sicher noch unsicher. **Strenger** ist nicht automatisch besser. Eine akzeptierte Abweichung gilt nur für exakten Wert, Gültigkeit, Verantwortliche und Ticket; Rohstatus und Ablaufdatum bleiben sichtbar.

Vor Änderungen in Intune immer Zielgruppen/Filter, Anwendbarkeit/Lizenz, Laufzeitstatus, Benutzer- und Geschäftswirkung, Pilot und Rollback mit berechtigten Administratoren prüfen. Der Auditor führt keine Änderung durch.
