from main import app, init_services

if __name__ == '__main__':
    init_services(start_agent=True)
    app.run(host='127.0.0.1', port=5000, debug=True)
