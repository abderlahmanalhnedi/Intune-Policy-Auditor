# Administratorhandbuch (Deutsch)

Python 3.11–3.13 und Node 24 LTS installieren, danach Setup, Build und Start gemäß README ausführen. Für den Normalbetrieb sind keine Administratorrechte nötig. Produktion verwendet einen Prozess auf `127.0.0.1:8765`.

SQLite, importierte Packs, optionale Berichte und Graph-Cache liegen im platformdirs-Anwendungsordner. Betriebssystem-Verschlüsselung und Benutzerrechte verwenden. Prüfverlauf und Berichtskopien sind standardmäßig aus; Löschfunktionen stehen unter Einstellungen bereit.

Für Tenant Mode nur eine öffentliche/native App-Registrierung mit Gerätecode und delegiertem `DeviceManagementConfiguration.Read.All` verwenden. Kein Client Secret, keine ReadWrite-Berechtigung. Beta-Hinweise und die Graph-Dokumentation beachten; eine echte Mandantenvalidierung ist noch nicht Teil der automatisierten Tests.

Knowledge Packs vor Aktivierung per UI/CLI validieren und durch eine zweite Person prüfen lassen. Exakte IDs, Werte, Versionen und offizielle Quellen dokumentieren. Mehrdeutige SCT-Datensätze bleiben `pending_review`.

Im Betrieb `/api/v1/health`, Version, lokale Logs, Speicherplatz, Pack-Alter/Validierung, Aufbewahrung und CI-Sicherheitsprüfungen überwachen. Nach Builds `python scripts/smoke.py` ausführen. Eine Bindung außerhalb von localhost erfordert gesonderte Freigabe, Netzwerk-/TLS-/Host-/CORS-Schutzmaßnahmen.
