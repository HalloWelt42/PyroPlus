/* Hilfetexte. Jeder Abschnitt hat eine stabile Kennung für Tiefenlinks aus der Oberfläche. */

export interface Abschnitt { id: string; titel: string; html: string; }

export const ABSCHNITTE: Abschnitt[] = [
  {
    id: 'erste-schritte', titel: 'Erste Schritte',
    html: `<h3>Erste Schritte</h3>
<p>PyroPlus steuert drei Dinge am Gehäuse: den <b>Lüfter</b>, die <b>LEDs</b> und das kleine <b>Display</b>. Jeder Bereich hat links in der Seitenleiste einen eigenen Eintrag. Der Schnellzugriff darunter schaltet alle drei ein oder aus.</p>
<p>Die Seitenleiste zeigt immer den Livezustand: Temperatur des Prozessors, die vier LED-Farben, wie sie die Hardware gerade meldet, und das Bild, das das Display gerade anzeigt.</p>
<h4>Begriffe</h4>
<dl>
<dt>Pixel</dt><dd>Ein Bildpunkt. Das Display hat 128 Punkte in der Breite und 64 in der Höhe.</dd>
<dt>Widget</dt><dd>Ein Element auf dem Display, zum Beispiel die Uhr oder ein Balken. Es verbindet eine Datenquelle mit einer Darstellungsart.</dd>
<dt>Bildschirm</dt><dd>Eine Zusammenstellung von Widgets. Mehrere Bildschirme wechseln sich in der Rotation ab.</dd>
</dl>`,
  },
  {
    id: 'display', titel: 'Display',
    html: `<h3>Display</h3>
<p>Oben stellst du die <b>Betriebsart</b> ein: <b>Rotation</b> zeigt alle aktiven Bildschirme nacheinander, <b>Fest</b> zeigt nur den gewählten, <b>Aus</b> schaltet das Display dunkel. Daneben das Intervall der Rotation und die Helligkeit.</p>
<p>Links liegt die Liste der Bildschirme. Der grün markierte wird gerade auf dem Display gezeigt, der blau markierte wird bearbeitet. Beides kann derselbe sein. Mit dem Schalter nimmst du einen Bildschirm aus der Rotation, ohne ihn zu löschen. Ziehen am Griff ändert die Reihenfolge, Doppelklick auf den Namen benennt um.</p>
<p>In der Mitte siehst du die Vorschau genau so, wie das Backend sie rendert. Das Bild auf dem Gerät ist dasselbe Bild. Rechts bearbeitest du das gewählte Widget, fügst neue hinzu oder wählst Bausteine.</p>`,
  },
  {
    id: 'bildschirme', titel: 'Bildschirme',
    html: `<h3>Bildschirme</h3>
<p><b>Neuer Bildschirm</b> legt eine leere Fläche an. Schneller geht es mit <b>Vorlagen</b>: fertige Bildschirme, die du einfügst und danach frei änderst. <b>Kopie</b> dupliziert den bearbeiteten Bildschirm.</p>
<p>Jeder Bildschirm kann eine eigene Anzeigedauer haben; ohne eigene Dauer gilt das Intervall aus der Kopfzeile. Der Knopf <b>Auf dem Display zeigen</b> schaltet sofort auf den bearbeiteten Bildschirm um und setzt die Rotation von dort fort.</p>
<p>Änderungen werden automatisch gespeichert. Das Abzeichen über der Vorschau zeigt, ob gerade gespeichert wird.</p>`,
  },
  {
    id: 'widgets', titel: 'Widgets einfügen und bearbeiten',
    html: `<h3>Widgets einfügen und bearbeiten</h3>
<p>Im Reiter <b>Hinzufügen</b> wählst du zuerst den Bereich (CPU, Wetter, Zeiten ...), dann die Quelle. Neben jeder Quelle steht ihr aktueller Wert. Danach wählst du die Darstellung; das neue Widget erscheint sofort als Vorschau an einer freien Stelle (Kennzeichen "Neu") und wird mit <b>Einfügen</b> übernommen. <b>Verwerfen</b>, der Knopf über dem Display, <b>Esc</b> oder <b>Entf</b> entfernen die Vorschau wieder, ohne etwas einzufügen. Die Vorschau im Reiter zeigt das Widget genau in seiner Pixelgröße.</p>
<p>Ein Klick auf ein Widget in der Vorschau wählt es und zeigt seine Eigenschaften; ein Baustein dagegen wird eingefügt und gewählt, die Liste der Bausteine bleibt dabei offen; <b>Umschalt</b> und Klick wählt mehrere. Ziehen verschiebt, die Pfeiltasten rücken um ein Pixel, mit Umschalt um acht. Rechtsklick öffnet das Menü mit Kopieren, Zentrieren, Verteilen, Reihenfolge und Löschen.</p>
<p>Oben im Reiter <b>Eigenschaften</b> stehen <b>Kopie</b>, <b>Sichern</b> und <b>Löschen</b>; die Taste <b>Entf</b> löscht ebenfalls. Unter Position setzt du X und Y direkt oder richtest aus: waagerecht und senkrecht zur Displaymitte, an den linken oder oberen Rand. Bei mehreren gewählten Widgets kommen Oben bündig, Links bündig und Verteilen dazu.</p>
<p><b>Sichern</b> legt ein Widget als eigenen Baustein ab, den du auf jedem Bildschirm wieder einfügen kannst.</p>`,
  },
  {
    id: 'darstellungsarten', titel: 'Darstellungsarten',
    html: `<h3>Darstellungsarten</h3>
<p>Jedes Widget verbindet eine Datenquelle mit einer Darstellungsart. Die Quelle liefert den Wert, die Darstellungsart bestimmt, wie er auf dem Display erscheint. Größen sind keine eigenen Arten, sondern Optionen; die Vorgaben (Klein, Mittel, Groß ...) setzen nur Skalierung oder Maße.</p>
<h4>Für Zahlen und Prozentwerte</h4>
<dl>
<dt>Zahl oder Text</dt><dd>Der Wert als Schrift. Skalierung von 1 bis 8, Breite und Höhe getrennt. Dezimalstellen und Tausendertrenner sind einstellbar.</dd>
<dt>Siebensegment</dt><dd>Ziffern wie auf einer Digitaluhr, Höhe frei von 7 bis 64 Pixeln. Doppelpunkt, Punkt und Minus gehören dazu; Buchstaben erscheinen in der Pixelschrift.</dd>
<dt>Symbol + Wert</dt><dd>Ein Symbol aus der Bibliothek, daneben der Wert. Ohne eigene Wahl nimmt das Backend das Symbol, das zur Quelle passt: Thermometer für Temperaturen, Prozessor für die Auslastung, Tropfen für die Feuchte.</dd>
<dt>Balken</dt><dd>Füllstand von 0 bis 100 Prozent. Für Werte ohne Prozentbezug rechnet das Backend um, zum Beispiel Temperatur bezogen auf 85 Grad.</dd>
<dt>Balken + Wert</dt><dd>Balken, rechts daneben der Wert.</dd>
<dt>Balken (Wert innen)</dt><dd>Balken mit dem Wert in der Mitte.</dd>
<dt>Säule</dt><dd>Senkrechter Balken, füllt sich von unten.</dd>
<dt>Stufen</dt><dd>Felder nebeneinander, gefüllt bis zum Wert; Anzahl 2 bis 32.</dd>
<dt>Halbkreis</dt><dd>Ein halber Ring, der sich mit dem Wert füllt. Der Wert steht in der Mitte. Radius 4 bis 32 Pixel.</dd>
<dt>Ring</dt><dd>Voller Ring, füllt sich von oben im Uhrzeigersinn; der Wert steht in der Mitte, wenn er hineinpasst.</dd>
<dt>Verlauf</dt><dd>Linie der letzten Minute, wahlweise als gefüllte Fläche. Nur für Quellen mit Verlaufsdaten: CPU, Temperatur, RAM, Drehzahl, Netzwerk.</dd>
</dl>
<h4>Für Texte und Zeiten</h4>
<dl>
<dt>Invertiert</dt><dd>Dunkle Schrift auf hellem Block.</dd>
<dt>Mit Rahmen</dt><dd>Schrift mit einem Pixel Rand.</dd>
<dt>Laufschrift</dt><dd>Der Text läuft von rechts nach links durch das Bild.</dd>
</dl>
<h4>Layout und Besonderes</h4>
<dl>
<dt>Symbol</dt><dd>Festes Symbol aus der Bibliothek in 8, 16, 24 oder 32 Pixeln, siehe Abschnitt Symbole.</dd>
<dt>Linie, Rahmen, Block, Trennlinie</dt><dd>Gestaltungselemente ohne Wert.</dd>
<dt>Lüftersymbol</dt><dd>Dreht sich mit der Drehzahl, wahlweise mit Zahl daneben.</dd>
<dt>Pixelbild</dt><dd>Frei gezeichnete Pixel, siehe Abschnitt Pixelbilder.</dd>
</dl>
<h4>Ausrichtung</h4>
<p>Mitte und Rechts beziehen sich auf eine Box; die Boxbreite legst du selbst fest. 128 Pixel ist das ganze Display, so zentrierst du eine Zeile.</p>`,
  },
  {
    id: 'datenquellen', titel: 'Datenquellen',
    html: `<h3>Datenquellen</h3>
<p>Alle Werte kommen vom Backend. Bereiche: <b>CPU</b> (Temperatur, Auslastung, Kerne), <b>Arbeitsspeicher</b>, <b>Laufwerke</b> (je erkanntes Laufwerk eigene Werte), <b>Netzwerk</b> (Adresse, Rechnername, Durchsatz), <b>Lüfter</b> (Drehzahl, Leistung, Stufe, Gehäuselüfter), <b>Zeiten</b> (Uhr, Datum, Laufzeit, Weltzeituhren), <b>Wetter</b> (aktuelle Werte je Ort), <b>Texte</b> (eigene Texte, mehrzeilig, Laufschrift) und <b>Layout</b>.</p>
<p>Zahlen formatiert das Backend nach den Optionen des Widgets: Dezimalstellen, Tausendertrenner, Text davor und danach. Der Probewert im Reiter Hinzufügen zeigt die Darstellung mit einem angenommenen Wert, zum Beispiel um zu sehen, wie 100 Prozent aussehen.</p>`,
  },
  {
    id: 'pixelbilder', titel: 'Pixelbilder',
    html: `<h3>Pixelbilder</h3>
<p>Ein Pixelbild ist ein Widget mit frei gesetzten Punkten. Füge es über die Bausteine ("Leeres Pixelbild") oder über Hinzufügen, Bereich Layout, Quelle Pixelbild ein. Ein gewähltes Pixelbild verschiebst und löschst du wie jedes andere Widget.</p>
<p>Das <b>Zeichnen</b> beginnt ausdrücklich: über den Knopf im Reiter Eigenschaften, per Doppelklick auf das Bild oder über das Kontextmenü. Dann wird der Rahmen des Bildes auf der Vorschau zum Zeichenbereich; alles außerhalb wird abgedunkelt. <b>Fertig</b> oder <b>Esc</b> beendet das Zeichnen.</p>
<dl>
<dt>Stift, Radierer</dt><dd>Linke Maustaste setzt, rechte löscht. Stiftbreite 1 bis 4.</dd>
<dt>Linie, Rechteck, Ellipse</dt><dd>Aufziehen; Formen wahlweise gefüllt.</dd>
<dt>Füllen</dt><dd>Zusammenhängende Fläche füllen.</dd>
<dt>Text</dt><dd>Setzt Text in der Pixelschrift des Displays an der Klickstelle ein.</dd>
<dt>Verschieben</dt><dd>Zieht den Bildinhalt im Rahmen.</dd>
</dl>
<p>Die Bildgröße ist frei (bis 128 mal 64). <b>Zuschneiden</b> verkleinert das Bild auf den gezeichneten Inhalt. Tasten im Zeichenmodus: P Stift, E Radierer, L Linie, R Rechteck, C Ellipse, F Füllen, T Text, V Verschieben.</p>`,
  },
  {
    id: 'symbole', titel: 'Symbole',
    html: `<h3>Symbole</h3>
<p>Die Symbolbibliothek liefert über 130 Symbole in den Gruppen Wetter, System, Netzwerk, Zeit, Status und Deko, jedes in 8, 16, 24 und 32 Pixeln. Sie werden aus der Symbolschrift der Oberfläche gerastert, damit Display und Oberfläche dieselbe Bildsprache sprechen.</p>
<p>Zwei Darstellungsarten nutzen sie: <b>Symbol</b> zeigt ein festes Symbol, <b>Symbol + Wert</b> stellt den Wert einer Quelle daneben. Bei Symbol + Wert wählt das Backend ohne eigene Wahl ein passendes Symbol; "Automatisch" in der Symbolwahl stellt das wieder her.</p>
<p>Das Lüftersymbol liegt in 32 Drehbildern vor und dreht sich mit der Drehzahl. Die Wettersymbole der fertigen Wetterbildschirme kommen aus derselben Bibliothek.</p>`,
  },
  {
    id: 'vorlagen', titel: 'Vorlagen und Bausteine',
    html: `<h3>Vorlagen und Bausteine</h3>
<p><b>Bildschirmvorlagen</b> sind fertige Bildschirme nach Gruppen: Uhr, System, Laufwerke, Netzwerk, Wetter. Eine Vorlage wird als Kopie eingefügt; danach ist jedes Widget darin frei änderbar. Die Wetterbildschirme "kompakt", "nächste Stunden" und "fünf Tage" sind feste Layouts mit Symbolen und haben nur einen Ort als Einstellung.</p>
<p><b>Bausteine</b> sind einzelne Widgets: mitgelieferte in den Gruppen Uhr, System, Laufwerke, Netzwerk, Lüfter, Wetter, Symbole und Layout, dazu eigene. Jede Kachel zeigt das Widget in seiner echten Pixelgröße mit den aktuellen Werten. Ein Klick fügt den Baustein an einer freien Stelle ein, danach lässt er sich wie jedes Widget verschieben, ändern und löschen. Eigene Bausteine entstehen über <b>Sichern</b> am gewählten Widget; über die Kachel lassen sie sich umbenennen und löschen.</p>`,
  },
  {
    id: 'wetterorte', titel: 'Wetterorte',
    html: `<h3>Wetterorte</h3>
<p>Wetterwerte brauchen einen Ort. Im Fenster Wetterorte suchst du eine Stadt und fügst sie hinzu; der erste Ort wird der <b>Vorgabeort</b>. Wetter-Widgets zeigen den Vorgabeort, wenn bei ihnen kein anderer Ort gewählt ist. So kannst du mehrere Orte auf verschiedenen Bildschirmen zeigen.</p>
<p>Die Werte lädt das Backend alle zehn Minuten von einem freien Wetterdienst ohne Anmeldung. "Alle laden" holt sie sofort.</p>`,
  },
  {
    id: 'profile', titel: 'Profile und Sicherung',
    html: `<h3>Profile und Sicherung</h3>
<p>Ein <b>Profil</b> sichert alle Bildschirme und das Wechselintervall unter einem Namen, zum Beispiel "Tag" und "Nacht". Laden ersetzt die aktuellen Bildschirme durch die des Profils.</p>
<p>Der <b>Export</b> schreibt alles (Bildschirme, Bausteine, Profile, Wetterorte) in eine Datei. Beim <b>Import</b> wählst du, ob ergänzt oder alles ersetzt wird. Ersetzen verlangt eine zweite Bestätigung.</p>
<p>Hat eine frühere Version Daten im Browser gespeichert, bietet das Fenster an, sie zu übernehmen. Danach liegen sie auf dem Pi und sind von jedem Gerät aus erreichbar.</p>`,
  },
  {
    id: 'luefter', titel: 'Lüfter',
    html: `<h3>Lüfter</h3>
<p>Es gibt zwei Lüfter. Der <b>Gehäuselüfter</b> kennt nur An und Aus und schaltet nach Schwellwerten: einschalten ab der oberen Temperatur, ausschalten unter der unteren. Der Abstand zwischen beiden verhindert ständiges Takten.</p>
<p>Der <b>CPU-Lüfter</b> läuft stufenlos nach einer Temperaturkurve. Punkte auf der Kurve lassen sich ziehen, hinzufügen und entfernen; die Profile Leise, Ausgewogen und Leistung sind fertige Kurven. <b>Hysterese</b>: Der Lüfter regelt erst herunter, wenn die Temperatur um diesen Wert gefallen ist. Ab 80 Grad läuft der Lüfter immer mit voller Leistung.</p>
<p>Mit <b>Simulation</b> prüfst du das Verhalten bei einer angenommenen Temperatur; LEDs und Lüfter reagieren dann wie im Ernstfall.</p>`,
  },
  {
    id: 'leds', titel: 'LEDs',
    html: `<h3>LEDs</h3>
<p>Die vier LEDs zeigen entweder eine <b>Temperaturfarbe</b> (blau kalt bis rot heiß) oder einen <b>Effekt</b>. Effekte sind in Gruppen sortiert: feste Farben, Animationen, Spielereien. Helligkeit und Geschwindigkeit gelten für alle Effekte.</p>
<p><b>Einzelne LEDs</b>: Im Einzelmodus bekommt jede LED ihre eigene Farbe. Die Farben in der Seitenleiste sind die Farben, die die Hardware gerade meldet, nicht eine Nachbildung.</p>`,
  },
  {
    id: 'tasten', titel: 'Tastenkürzel',
    html: `<h3>Tastenkürzel im Display-Editor</h3>
<dl>
<dt>Pfeile</dt><dd>Gewählte Widgets um ein Pixel rücken, mit Umschalt um acht.</dd>
<dt>Entf</dt><dd>Gewählte Widgets löschen.</dd>
<dt>Strg + Z, Strg + Y</dt><dd>Rückgängig, wiederholen.</dd>
<dt>Strg + D</dt><dd>Gewählte Widgets kopieren.</dd>
<dt>Strg + A</dt><dd>Alle Widgets wählen.</dd>
<dt>Esc</dt><dd>Auswahl aufheben.</dd>
<dt>P, E, L, R, C, F, T, V</dt><dd>Zeichenwerkzeuge im Pixelbild.</dd>
</dl>`,
  },
];
