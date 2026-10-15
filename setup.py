"""Execute uma vez: cria ou redefine contas sem senhas predefinidas."""
import getpass, argparse
from db import connect,init,hash_password

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Criar usuários do PPGCA')
    parser.add_argument('--user',choices=['ernandes','maria'])
    args=parser.parse_args()
    init()
    people={'ernandes':'Ernandes Sobreira Oliveira Junior','maria':'Maria Ribeiro'}
    for username,display in people.items():
        if args.user and username!=args.user:continue
        print(f'\nUsuário: {username} — {display}')
        pw=getpass.getpass('Defina senha (12+ caracteres): ')
        if len(pw)<12: raise SystemExit('Senha curta; não foi salva.')
        if pw!=getpass.getpass('Repita a senha: '):raise SystemExit('As senhas diferem.')
        with connect() as c:
            c.execute('INSERT INTO users(username,display_name,password_hash,role) VALUES(?,?,?,?) ON CONFLICT(username) DO UPDATE SET display_name=excluded.display_name, password_hash=excluded.password_hash',(username,display,hash_password(pw),'admin' if username=='ernandes' else 'editor'))
        print('Conta preparada.')
    print('\nInicie com: python -m uvicorn app:app --host 127.0.0.1 --port 8000')
