import os
from datetime import datetime, date

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from jinja2 import DictLoader

db = SQLAlchemy()

STATUS = {
    "recebido": "Recebido",
    "em_preparo": "Em preparo",
    "concluido": "Concluído",
}


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="recebido")
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    itens = db.relationship("Item", backref="pedido", cascade="all, delete-orphan")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    produto = db.Column(db.String(80), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)


TEMPLATES = {
    "base.html": """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Açaí da Vila</title>
<style>
  body{font-family:system-ui,sans-serif;margin:0;background:#faf7ff;color:#1b1030;line-height:1.5}
  header{background:#4a1d7a;color:#fff;padding:1rem}
  header a{color:#fff;margin-right:1rem;font-weight:bold;display:inline-block;min-height:44px;line-height:44px}
  main{max-width:720px;margin:0 auto;padding:1rem}
  label{display:block;font-weight:bold;margin-top:.75rem}
  input,select,button,.btn{font-size:1rem;min-height:44px;padding:.4rem .6rem;border:2px solid #4a1d7a;border-radius:6px;box-sizing:border-box}
  input{width:100%}
  button,.btn{background:#4a1d7a;color:#fff;cursor:pointer;text-decoration:none;display:inline-block}
  :focus-visible{outline:4px solid #ffb703;outline-offset:2px}
  .alert{padding:.75rem;border-radius:6px;margin:1rem 0;border-left:8px solid}
  .alert-success{background:#e6f7ec;border-color:#1b7a3d}
  .alert-error{background:#fde8e8;border-color:#b3261e}
  .card{background:#fff;border:1px solid #d9c9f0;border-radius:8px;padding:1rem;margin:1rem 0}
  .badge{padding:.2rem .6rem;border-radius:999px;font-weight:bold;border:2px solid #4a1d7a}
  .row{display:grid;grid-template-columns:2fr 1fr;gap:.5rem}
</style>
</head>
<body>
<header>
  <a href="{{ url_for('lista') }}">Pedidos do dia</a>
  <a href="{{ url_for('novo') }}">Novo pedido</a>
</header>
<main>
  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in msgs %}
      <div class="alert alert-{{ cat }}" role="{{ 'alert' if cat == 'error' else 'status' }}">
        <strong>{{ 'Erro:' if cat == 'error' else 'Sucesso:' }}</strong> {{ msg }}
      </div>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</main>
</body>
</html>""",
    "lista.html": """{% extends "base.html" %}
{% block content %}
<h1>Pedidos de hoje</h1>
{% for p in pedidos %}
<section class="card" aria-labelledby="p{{ p.id }}">
  <h2 id="p{{ p.id }}">#{{ p.id }} — {{ p.cliente }}</h2>
  <p>Status: <span class="badge">{{ status[p.status] }}</span>
     · {{ p.criado_em.strftime('%H:%M') }}</p>
  <ul>
    {% for i in p.itens %}<li>{{ i.quantidade }}x {{ i.produto }}</li>{% endfor %}
  </ul>
  <form method="post" action="{{ url_for('atualizar_status', pedido_id=p.id) }}">
    <label for="s{{ p.id }}">Alterar status</label>
    <select id="s{{ p.id }}" name="status">
      {% for k, v in status.items() %}
        <option value="{{ k }}" {{ 'selected' if k == p.status }}>{{ v }}</option>
      {% endfor %}
    </select>
    <button type="submit">Atualizar</button>
  </form>
</section>
{% else %}
<p>Nenhum pedido registrado hoje.</p>
{% endfor %}
{% endblock %}""",
    "novo.html": """{% extends "base.html" %}
{% block content %}
<h1>Novo pedido</h1>
<form method="post" novalidate>
  <label for="cliente">Nome do cliente</label>
  <input id="cliente" name="cliente" maxlength="80" required value="{{ cliente or '' }}">
  <h2>Itens</h2>
  {% for n in range(1, 6) %}
  <div class="row">
    <div>
      <label for="produto{{ n }}">Produto {{ n }}</label>
      <input id="produto{{ n }}" name="produto" maxlength="80">
    </div>
    <div>
      <label for="qtd{{ n }}">Quantidade</label>
      <input id="qtd{{ n }}" name="quantidade" type="number" min="1" max="99" inputmode="numeric">
    </div>
  </div>
  {% endfor %}
  <p><button type="submit">Registrar pedido</button></p>
</form>
{% endblock %}""",
}


def create_app(config=None):
    app = Flask(__name__)
    url = os.environ.get("DATABASE_URL", "sqlite:///acai.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=url,
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-em-producao"),
    )
    if config:
        app.config.update(config)

    app.jinja_loader = DictLoader(TEMPLATES)
    db.init_app(app)

    @app.route("/")
    def lista():
        inicio = datetime.combine(date.today(), datetime.min.time())
        pedidos = (
            Pedido.query.filter(Pedido.criado_em >= inicio)
            .order_by(Pedido.criado_em.desc())
            .all()
        )
        return render_template("lista.html", pedidos=pedidos, status=STATUS)

    @app.route("/novo", methods=["GET", "POST"])
    def novo():
        if request.method == "GET":
            return render_template("novo.html")

        cliente = request.form.get("cliente", "").strip()
        produtos = request.form.getlist("produto")
        quantidades = request.form.getlist("quantidade")

        itens, erro = [], None
        for prod, qtd in zip(produtos, quantidades):
            prod = prod.strip()
            if not prod and not qtd.strip():
                continue
            try:
                q = int(qtd)
            except ValueError:
                q = 0
            if not prod or not 1 <= q <= 99:
                erro = "Cada item precisa de produto e quantidade entre 1 e 99."
                break
            itens.append(Item(produto=prod, quantidade=q))

        if not cliente:
            erro = "Informe o nome do cliente."
        elif not erro and not itens:
            erro = "Adicione pelo menos um item."

        if erro:
            flash(erro, "error")
            return render_template("novo.html", cliente=cliente), 400

        pedido = Pedido(cliente=cliente, itens=itens)
        db.session.add(pedido)
        db.session.commit()
        flash(f"Pedido #{pedido.id} registrado com sucesso.", "success")
        return redirect(url_for("lista"))

    @app.post("/pedido/<int:pedido_id>/status")
    def atualizar_status(pedido_id):
        pedido = db.get_or_404(Pedido, pedido_id)
        novo_status = request.form.get("status")
        if novo_status not in STATUS:
            flash("Status inválido.", "error")
            return redirect(url_for("lista")), 400
        pedido.status = novo_status
        db.session.commit()
        flash(f"Pedido #{pedido.id} agora está: {STATUS[novo_status]}.", "success")
        return redirect(url_for("lista"))

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")