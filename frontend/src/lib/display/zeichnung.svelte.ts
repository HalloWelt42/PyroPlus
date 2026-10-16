/* Zustand der Zeichenwerkzeuge für Pixelbilder. */

export type Werkzeug = 'stift' | 'radierer' | 'linie' | 'rechteck' | 'ellipse' | 'fuellen' | 'text' | 'verschieben';

class Zeichnung {
  werkzeug = $state<Werkzeug>('stift');
  breite = $state(1);
  gefuellt = $state(false);
  text = $state('Hallo');
}

export const zeichnung = new Zeichnung();

export const WERKZEUGE: Array<{ id: Werkzeug; symbol: string; titel: string; taste: string }> = [
  { id: 'stift', symbol: 'fa-pen', titel: 'Stift: Pixel setzen; rechte Maustaste löscht', taste: 'P' },
  { id: 'radierer', symbol: 'fa-eraser', titel: 'Radierer: Pixel löschen', taste: 'E' },
  { id: 'linie', symbol: 'fa-minus', titel: 'Linie von Punkt zu Punkt ziehen', taste: 'L' },
  { id: 'rechteck', symbol: 'fa-square', titel: 'Rechteck aufziehen', taste: 'R' },
  { id: 'ellipse', symbol: 'fa-circle', titel: 'Ellipse aufziehen', taste: 'C' },
  { id: 'fuellen', symbol: 'fa-fill-drip', titel: 'Zusammenhängende Fläche füllen', taste: 'F' },
  { id: 'text', symbol: 'fa-font', titel: 'Text in Pixelschrift an der Klickstelle einsetzen', taste: 'T' },
  { id: 'verschieben', symbol: 'fa-up-down-left-right', titel: 'Bildinhalt im Rahmen verschieben', taste: 'V' },
];
