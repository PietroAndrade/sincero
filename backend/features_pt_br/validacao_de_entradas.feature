# language: pt
Funcionalidade: Validação de entradas
  Entradas inválidas são rejeitadas com uma mensagem clara em vez de produzir uma
  simulação enganosa.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Esquema do Cenário: Dados impossíveis do imóvel são rejeitados
    Dado um imóvel "X" anunciado por R$ <preco> com <meses> meses restantes até a entrega
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "<erro>"

    Exemplos:
      | preco      | meses | erro                                                    |
      | 0,00       | 12    | o preço de tabela deve ser maior que zero               |
      | 440.000,00 | 0     | os meses restantes até a entrega devem ser pelo menos 1 |

