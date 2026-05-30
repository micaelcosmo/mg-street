"""Camada de acesso a dados: isola o SQL cru das rotas.

Cada módulo cobre uma entidade e expõe funções que recebem a conexão psycopg2
(`conn`) e executam o SQL, retornando dados crus (tuplas/None) para as rotas
transformarem na resposta HTTP.
"""
