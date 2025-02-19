from flask import Flask, render_template, url_for, request, redirect, session
from flask.wrappers import Response
from werkzeug.datastructures import UpdateDictMixin
from werkzeug.security import generate_password_hash, check_password_hash

import mariadb
import ast
import io
import csv
konekcija = mariadb.connect(
    user = "root",
    password = "",
    host = "localhost",
    port = 3307,
    database = "evidencija_studenata"
)

kursor = konekcija.cursor(dictionary = True)

from flask_mail import Mail, Message

app = Flask(__name__)

app.secret_key = "tajni_kljuc_aplikacije"


app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "evidencija.atvss@gmail.com"
app.config["MAIL_PASSWORD"] = "atvss123loz"
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)

def ulogovan():
    if "ulogovan_korisnik" in session:
        return True
    else:
        return False

def rola():
    if ulogovan():
        return ast.literal_eval(session["ulogovan_korisnik"]).pop("rola")

def send_email(ime, prezime, email, lozinka):
    msg = Message(
        subject = "Korisnicki nalog",
        sender= "ATVSS Evidencija studenata",
        recipients = [email],
    )
    msg.html = render_template("email.html", ime = ime, prezime = prezime, lozinka = lozinka)
    mail.send(msg)
    return "Sent"

## EXPORT ##
@app.route("/export/<tip>")
def export(tip):
    switch = {
        "studenti": "SELECT * FROM studenti",
        "korisnici": "SELECT * FROM korisnici",
        "predmeti": "SELECT * FROM predmeti",
    }

    upit = switch.get(tip)
    kursor.execute(upit)
    rezultat = kursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    for row in rezultat:
        red = []
        for value in row.values():
            red.append(str(value))
        writer.writerow(red)

    output.seek(0)
    return Response(
        output,
        mimetype= "text/csv",
        headers={"Content-Disposition": "attachment;filename= " + tip + ".csv"},
        )

## LOG ##
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    elif request.method == 'POST':
        forma = request.form
        upit = "SELECT * FROM korisnici WHERE email = %s"
        vrednost = (forma["email"],)
        kursor.execute(upit, vrednost)
        korisnik = kursor.fetchone()
        if check_password_hash(korisnik["lozinka"], forma["lozinka"]):
            session["ulogovani_korisnik"] = str(korisnik)
            return redirect(url_for("studenti"))
        else:
            return render_template("login.html")

@app.route("/logout", methods=['GET'])
def logout():
    session.pop("ulogovani_korisnik", None)
    return redirect(url_for("login"))
## KORISNICI ##
@app.route("/korisnici", methods=['GET'])
def korisnici():
    upit = "SELECT * FROM korisnici"
    kursor.execute(upit)
    korisnici = kursor.fetchall()

    return render_template("korisnici.html", korisnici = korisnici)

@app.route("/korisnik_brisanje/<id>", methods=['GET', 'POST'])
def korisnik_brisanje(id):
        upit = """ DELETE FROM korisnici WHERE id = %s
        """
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("korisnici"))

@app.route("/korisnik_izmena/<id>", methods=['GET', 'POST'])
def korisnik_izmena(id):
    if request.method == 'GET':
        upit = "SELECT * FROM korisnici WHERE id = %s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        korisnik = kursor.fetchone()
        return render_template("korisnik_izmena.html", korisnik = korisnik)
    elif request.method == 'POST':
        forma = request.form
        hashovana_lozinka = generate_password_hash(forma["lozinka"])
        vrednosti = (
            forma["ime"],
            forma["prezime"],
            forma["email"],
            forma["rola"],
            hashovana_lozinka,
            id,
        )
        upit = """ UPDATE korisnici SET
        ime = %s,
        prezime = %s,
        email = %s,
        rola = %s,
        lozinka = %s,
        WHERE id = %s
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("korisnici"))

@app.route("/korisnik_novi", methods=['GET', 'POST'])
def korisnik_novi():
    if request.method == 'GET':
        return render_template("korisnik_novi.html")
    elif request.method == 'POST':
        forma = request.form
        hesovana_lozinka = generate_password_hash(forma["lozinka"])
        vrednosti = (
            forma["ime"],
            forma["prezime"],
            forma["email"],
            hesovana_lozinka,
            forma["rola"]
        )
        upit = """ INSERT INTO
        korisnici(ime, prezime, email, lozinka, rola)
        VALUES (%s, %s, %s, %s, %s)
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        send_email(forma["ime"], forma["prezime"], forma["email"], forma["lozinka"])
        return redirect(url_for("korisnici"))

## STUDENTI ##
@app.route("/studenti", methods=['GET'])
def studenti():
    upit = "SELECT * FROM studenti"
    kursor.execute(upit)
    studenti = kursor.fetchall()
    return render_template("studenti.html", studenti = studenti)

@app.route("/student_novi", methods=['GET', 'POST'])
def student_novi():
    if request.method == 'GET':
        return render_template("student_novi.html")
    elif request.method == 'POST':
        forma = request.form
        vrednosti = (
            forma["broj_indeksa"],
            forma["ime"],
            forma["ime_roditelja"],
            forma["prezime"],
            forma["email"],
            forma["broj_telefona"],
            forma["godina_studija"],
            forma["datum_rodjenja"],
            "123456",
            "0",
            "0",
        )
        upit = """ INSERT INTO
        studenti(broj_indeksa, ime, ime_roditelja, prezime, email, broj_telefona, godina_studija, datum_rodjenja, jmbg, espb, prosek_ocena)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("studenti"))

@app.route("/student_izmena/<id>", methods=['GET', 'POST'])
def student_izmena(id):
    if request.method == 'GET':
        upit = "SELECT * FROM studenti WHERE id = %s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        student = kursor.fetchone()
        return render_template("student_izmena.html", student = student)
    elif request.method == 'POST':
        forma = request.form
        vrednosti = (
            forma["broj_indeksa"],
            forma["ime"],
            forma["ime_roditelja"],
            forma["prezime"],
            forma["email"],
            forma["broj_telefona"],
            forma["godina_studija"],
            forma["datum_rodjenja"],
            forma["jmbg"],
            id,
        )
        upit = """ UPDATE studenti SET
        broj_indeksa = %s,
        ime = %s,
        ime_roditelja = %s,
        prezime = %s,
        email = %s,
        broj_telefona = %s,
        godina_studija = %s,
        datum_rodjenja = %s,
        jmbg = %s
        WHERE id = %s
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("studenti"))

@app.route("/student_brisanje/<id>", methods=['GET', 'POST'])
def student_brisanje(id):
        upit = """ DELETE FROM studenti WHERE id = %s
        """
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("studenti"))


@app.route("/student/<id>", methods=['GET', 'POST'])
def student(id):
    upit = "SELECT * FROM studenti WHERE id = %s"
    vrednost = (id,)
    kursor.execute(upit, vrednost)
    student = kursor.fetchone()

    upit = "SELECT * FROM predmeti"
    kursor.execute(upit)
    predmeti = kursor.fetchall()

    upit = "SELECT predmeti.sifra, predmeti.naziv, predmeti.godina_studija, predmeti.obavezni_izborni, predmeti.espb, ocene.ocena FROM ocene JOIN predmeti ON ocene.predmet_id = predmeti.id WHERE student_id = %s"
    vrednost = (id,)
    kursor.execute(upit, vrednost)
    ocene = kursor.fetchall()
    return render_template("student.html", student = student, predmeti = predmeti, ocene = ocene)


@app.route("/ocena_nova/<id>", methods = ['GET', 'POST'])
def ocena_nova(id):
    upit = """
    INSERT INTO ocene(student_id, predmet_id, ocena, datum)
    VALUES(%s, %s, %s, %s)

    """
    forma = request.form
    vrednosti = (id, forma['predmet_id'], forma['ocena'], forma['datum'])
    kursor.execute(upit, vrednosti)
    konekcija.commit()

    upit = "SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id = %s"
    vrednost = (id,)
    kursor.execute(upit, vrednost)
    prosek_ocena = kursor.fetchone()

    upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id = %s)"
    vrednost = (id,)
    kursor.execute(upit, vrednost)
    espb = kursor.fetchone()

    upit = "UPDATE studenti SET espb = %s, prosek_ocena = %s WHERE id = %s"
    vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
    kursor.execute(upit, vrednosti)
    konekcija.commit()
    return redirect(url_for('student', id = id))

@app.route("/ocena_izmena/<id>/<ocena_id>", methods = ['GET', 'POST'])
def ocena_izmena(id, ocena_id):
    if request.method == 'GET':
        upit = "SELECT * FROM studenti WHERE id = %s"
        vrednost = (id,)
        kursor.execution(upit, vrednost)
        student = kursor.fetchone()

        upit = "SELECT * FROM predmeti"
        kursor.execute(upit)
        predmeti = kursor.fetchall()

        upit = "SELECT predmeti.sifra, predmeti.naziv, predmeti.godina_studija, predmeti.obavezni_izborni, predmeti.espb, ocene.ocena, ocene.id FROM ocene JOIN predmeti ON ocene.predmet_id = predmet_id"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        ocene = kursor.fetchall()

        upit = "SELECT * FROM ocene WHERE id = %s"
        vrednost = (ocena_id,)
        kursor.execute(upit, vrednost)
        data_ocena = kursor.fetchone()
        return render_template("ocena_izmena.html", predmeti = predmeti, ocene = ocene, data_ocena = data_ocena, id = id)
    elif request.method == 'POST':
        forma = request.form
        vrednosti = (
            forma['predmet_id'],
            forma['ocena_id'],
            forma['datum'],
            ocena_id,
        )

        upit = """ UPDATE ocene SET
        predmet_id = %s,
        ocena = %s,
        datum = %s,
        WHERE id = %s,
        """
        kursor.execute(upit, vrednosti)

        upit = "SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id = %s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        prosek_ocena = kursor.fetchone()
        upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id = %s)"
        vrednost = (id, )
        kursor.execute(upit, vrednost)
        espb = kursor.fetchone()

        upit = "UPDATE studenti SET espb = %s, prosek_ocena = %s WHERE id = %s"
        vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("student"), id = id)

@app.route("/ocena_brisanje/<id>/<ocena_id>")
def ocena_brisanje(id, ocena_id):
    upit = "DELETE FROM ocene WHERE id = %s"
    vrednost = (ocena_id,)
    kursor.execute(upit, vrednost)
    prosek_ocena = kursor.fetchone()

    upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id = %s)"
    vrednost = (id, )
    kursor.execute(upit, vrednost)
    espb = kursor.fetchone()

    upit = "UPDATE studenti SET espb = %s, prosek_ocena = %s WHERE id = %s"
    vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
    kursor.execute(upit, vrednosti)
    
    konekcija.commit()
    return redirect(url_for("student", id = id))

## PREDMETI ##
@app.route("/predmeti", methods=['GET'])
def predmeti():
    upit = "SELECT * FROM predmeti"
    kursor.execute(upit)
    predmeti = kursor.fetchall()
    return render_template("predmeti.html", predmeti = predmeti)

@app.route("/predmet_novi", methods=['GET', 'POST'])
def predmet_novi():
    if request.method == 'GET':
        return render_template("predmet_novi.html")
    elif request.method == 'POST':
        forma = request.form
        vrednosti = (
            forma["sifra"],
            forma["naziv"],
            forma["godina_studija"],
            forma["espb"],
            forma["obavezni_izborni"]
        )
        upit = """ INSERT INTO
        predmeti(sifra, naziv, godina_studija, espb, obavezni_izborni)
        VALUES (%s, %s, %s, %s, %s)
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("predmeti"))

@app.route("/predmet_izmena/<id>", methods=['GET', 'POST'])
def predmet_izmena(id):
    if request.method == 'GET':
        upit = "SELECT * FROM predmeti WHERE id = %s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        predmet = kursor.fetchone()
        return render_template("predmet_izmena.html", predmet = predmet)
    elif request.method == 'POST':
        forma = request.form
        vrednosti = (
            forma["sifra"],
            forma["naziv"],
            forma["godina_studija"],
            forma["espb"],
            forma["obavezni_izborni"],
            id,
        )
        upit = """ UPDATE predmeti SET
        sifra = %s,
        naziv = %s,
        godina_studija = %s,
        espb = %s,
        obavezni_izborni = %s
        WHERE id = %s
        """
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for("predmeti"))

@app.route("/predmet_brisanje/<id>", methods=['GET', 'POST'])
def predmet_brisanje(id):
        upit = """ DELETE FROM predmeti WHERE id = %s
        """
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("predmeti"))


app.run(debug=True)