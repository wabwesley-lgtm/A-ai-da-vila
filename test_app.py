import pytest

from app import create_app, db, Pedido, Item


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def criar_pedido(app, cliente="Ana"):
    with app.app_context():
        pedido = Pedido(
            cliente=cliente,
            itens=[Item(produto="Açaí 300ml", quantidade=1)],
        )
        db.session.add(pedido)
        db.session.commit()
        return pedido.id


def test_lista_vazia(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Nenhum pedido registrado hoje" in resp.get_data(as_text=True)


def test_tela_novo_pedido(client):
    resp = client.get("/novo")
    assert resp.status_code == 200
    assert "Novo pedido" in resp.get_data(as_text=True)


def test_registrar_pedido_valido(client):
    resp = client.post(
        "/novo",
        data={"cliente": "Ana", "produto": ["Açaí 500ml"], "quantidade": ["2"]},
        follow_redirects=True,
    )
    texto = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "registrado com sucesso" in texto
    assert "Ana" in texto
    assert "2x Açaí 500ml" in texto


def test_pedido_sem_cliente(client):
    resp = client.post(
        "/novo",
        data={"cliente": "", "produto": ["Açaí"], "quantidade": ["1"]},
    )
    assert resp.status_code == 400
    assert "Informe o nome do cliente" in resp.get_data(as_text=True)


def test_pedido_sem_itens(client):
    resp = client.post(
        "/novo",
        data={"cliente": "Ana", "produto": [""], "quantidade": [""]},
    )
    assert resp.status_code == 400
    assert "Adicione pelo menos um item" in resp.get_data(as_text=True)


def test_quantidade_invalida(client):
    resp = client.post(
        "/novo",
        data={"cliente": "Ana", "produto": ["Açaí"], "quantidade": ["0"]},
    )
    assert resp.status_code == 400
    assert "quantidade entre 1 e 99" in resp.get_data(as_text=True)


def test_atualizar_status(client, app):
    pedido_id = criar_pedido(app)
    resp = client.post(
        f"/pedido/{pedido_id}/status",
        data={"status": "em_preparo"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Em preparo" in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Pedido, pedido_id).status == "em_preparo"


def test_status_invalido(client, app):
    pedido_id = criar_pedido(app)
    resp = client.post(f"/pedido/{pedido_id}/status", data={"status": "xyz"})
    assert resp.status_code == 400
    with app.app_context():
        assert db.session.get(Pedido, pedido_id).status == "recebido"


def test_pedido_inexistente(client):
    resp = client.post("/pedido/999/status", data={"status": "concluido"})
    assert resp.status_code == 404