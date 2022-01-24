from ast import Pass
import time
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from . import db
from Crypto.Cipher import AES
from .models import Password, User, Shared_passwords
import sys
from sqlalchemy.orm import Session
from .auth import hash_password, check_password

main = Blueprint('main', __name__)

class SharedPasswords:
    def __init__(self, user_name, passwords ):
        self.user_name = user_name
        self.passwords = passwords

def encryptAES(userId, password):
    padding_size = 16 - len(password)%16
    password += padding_size * b'+'
    key = User.query.filter_by(id=userId).first().password[0:16].encode('utf-8')
    iv = User.query.filter_by(id=userId).first().password[-16:].encode('utf-8')
    aes = AES.new(key, AES.MODE_CBC, iv)
    encrypted_1 = aes.encrypt(password)
    key = b'tsEGn1UgYBmo6rP8'
    iv = b'1khRro6vym8fSKWB'
    aes = AES.new(key, AES.MODE_CBC, iv)
    return aes.encrypt(encrypted_1)

def decryptAES(userId, password):
    with db.session.no_autoflush:
        key = b'tsEGn1UgYBmo6rP8'
        iv = b'1khRro6vym8fSKWB'
        aes = AES.new(key, AES.MODE_CBC, iv)
        decrypted_1 = aes.decrypt(password)
        key = User.query.filter_by(id=userId).first().password[0:16].encode('utf-8')
        iv = User.query.filter_by(id=userId).first().password[-16:].encode('utf-8')
        aes = AES.new(key, AES.MODE_CBC, iv)
        return aes.decrypt(decrypted_1).decode('utf-8').replace("+", "")

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    with db.session.no_autoflush:
        passwords = Password.query.filter_by(userId=current_user.id).all()
        for password in passwords:
            password.password = decryptAES(current_user.id, password.password)
        shared_passwords_with_names = []
        for shared in Shared_passwords.query.filter_by(idTo=current_user.id).all():
            shared_passwords = []
            for password in Password.query.filter_by(userId=shared.idFrom).all():
                password.password = decryptAES(shared.idFrom, password.password)
                shared_passwords.append(password)
            shared_passwords_with_names.append(SharedPasswords(User.query.filter_by(id=shared.idFrom).first().name, shared_passwords))
        return render_template('profile.html', name=current_user.name, passwords=passwords, shared_passwords=shared_passwords_with_names)

@main.route('/add_password')
@login_required
def add_password():
    return render_template('add_password.html')

@main.route('/add_password', methods=['POST'])
def add_password_post():
    name = request.form.get('name')
    password = request.form.get('password').encode('utf-8')
    new_password = Password(name = name, userId=current_user.id, password=encryptAES(current_user.id, password))
    db.session.add(new_password)
    db.session.commit()
    return redirect(url_for('main.profile'))

@main.route('/share_passwords')
@login_required
def share_passwords():
    return render_template('share_passwords.html')

@main.route('/share_passwords', methods=['POST'])
def share_passwords_post():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('No user with email: ' + email)
        return redirect(url_for('main.share_passwords'))
    shared = Shared_passwords.query.filter_by(idFrom = current_user.id, idTo=user.id).first()
    if shared:
        flash('Passwords already shared with: ' + email)
        return redirect(url_for('main.share_passwords'))
    new_shared_passwords = Shared_passwords(idFrom = current_user.id, idTo=user.id)
    db.session.add(new_shared_passwords)
    db.session.commit()
    return redirect(url_for('main.share_passwords'))

@main.route('/change_password')
@login_required
def change_password():
    return render_template('change_password.html')

@main.route('/change_password', methods=['POST'])
@login_required
def change_password_post():
    password_old = request.form.get('password_old')
    password_new = request.form.get('password_new')
    if(current_user.password != hash_password(password_old, current_user.salt)):
        time.sleep(2)
        flash('Please check your old password and try again')
        return redirect(url_for('main.change_password'))
    if(not check_password(password_new)):
        flash('Password needs to be at least 8 characters and include at least one: uppercase letter, lowecase letter, digit and [!, @, #, $, %, ^, &, *]')
        return redirect(url_for('main.change_password'))
    for password in Password.query.filter_by(userId = current_user.id).all():
        password.password = decryptAES(current_user.id, password.password)
    current_user.password = hash_password(password_new, current_user.salt)
    for password in Password.query.filter_by(userId = current_user.id).all():
        password.password = encryptAES(current_user.id, password.password.encode('utf-8'))
    db.session.commit()
    return redirect(url_for('main.profile'))