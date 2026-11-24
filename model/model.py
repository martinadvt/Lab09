from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        #aggiungo gli attributi di supporto alla ricorsione
        self._escursioni_parco = []  #salvo qui le escursioni del parco selezionato
        self._max_giorni = None  #salvo il numero massimo di giorni (None se non c'è limite)
        self._max_budget = None  #salvo il budget massimo (None se non c'è limite)

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()
        if relazioni is None:
            return
        for rel in relazioni:
            id_escursione = rel["id_escursione"]
            id_punto_interesse = rel["id_punto_interesse"]

            escursione = self.escursioni_map[id_escursione]
            punto_interesse = self.punti_interesse_map[id_punto_interesse]

            #collego il punto di interesse all'escursione e viceversa (relazione N:N)
            escursione.punti_interesse.add(punto_interesse)
            punto_interesse.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        #memorizzo i vincoli per usarli nella ricorsione
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        #considero solo le escursioni del parco selezionato
        self._escursioni_parco = [esc for esc in self.escursioni_map.values() if esc.id_parco == id_parco]

        #avvio la ricorsione partendo da un pacchetto vuoto
        self._ricorsione(0, [], 0, 0, 0, set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        #A - ogni soluzione parziale è valida, quindi controllo se migliora l'ottimo e in caso la salvo
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._costo = costo_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()

        #parto da start_index così non considero due volte la stessa combinazione e le escursioni restano tutte diverse
        for i in range(start_index, len(self._escursioni_parco)):
            escursione = self._escursioni_parco[i]

            #C - controllo i vincoli: durata, budget e nessun punto di interesse duplicato
            nuova_durata = durata_corrente + escursione.durata_giorni
            nuovo_costo = costo_corrente + escursione.costo
            if self._max_giorni is not None and nuova_durata > self._max_giorni:
                continue
            if self._max_budget is not None and nuovo_costo > self._max_budget:
                continue
            if not punti_usati.isdisjoint(escursione.punti_interesse):
                continue

            #D - calcolo il voto dell'escursione e la aggiungo al pacchetto parziale insieme ai suoi punti
            valore_escursione = sum(p.voto_visitatori for p in escursione.punti_interesse)
            pacchetto_parziale.append(escursione)
            punti_usati.update(escursione.punti_interesse)

            #E - richiamo la ricorsione passando all'escursione successiva
            self._ricorsione(i + 1, pacchetto_parziale, nuova_durata, nuovo_costo,
                             valore_corrente + valore_escursione, punti_usati)

            #F - faccio backtracking togliendo l'escursione e i suoi punti di interesse
            pacchetto_parziale.pop()
            punti_usati.difference_update(escursione.punti_interesse)
