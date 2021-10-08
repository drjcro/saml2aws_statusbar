# Saml2aws timer
A little statusbar that shows you how long until saml2aws credentials will expire 

# Install requirements for app
```bash
$ pip install -r ./requirements.txt

```
# Run app
```bash
$ python app.py
```

Recommended use [PM2](https://github.com/Unitech/PM2) for work on background.

```bash
$ pm2 start --name awesomeapp --no-autorestart app.py
or if you using specific python version and want logs 
$ pm2 start --name awesomeapp --no-autorestart `pwd`/app.py -l `pwd`/app.log --interpreter /usr/local/bin/python3

# Stop app
$ pm2 stop awesomeapp
```

