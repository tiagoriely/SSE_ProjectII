# SSE_ProjectII

### GitHub
Clone the repository
```
git clone https://github.com/tiagoriely/SSE_ProjectII.git
```
Push Changes to GitHub
```
git add .
git commit -m "Commit message"
git push origin main
```

Pull Latest Changes
```
git pull
```


## Creating virtual environment
Create the venv
```
python3 -m venv venv
```

Activate venv
```
source venv/bin/activate
```

Install Flask
```
pip install flask
```

Install packages
```
pip install -r requirements.txt
```

## Run Flask App
Be careful, the port may have been changed
```
flask --app app.py run --host=0.0.0.0 --port 8000
```

