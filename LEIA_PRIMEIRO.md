# Dashboard atualizado — Rastreador Solar

## Compatível com o código atual do grupo
Esta versão lê diretamente a saída atual do firmware, sem precisar modificá-la:
```
Sup: 1800 | Inf: 1800 | Esq: 2200 | Dir: 1000 | DifV: 0.000 | DifH: 0.788 | AngV: 90
```
Os valores acima exemplificam apenas o formato. A interface começa sem dados; não usa esses números como evidência real.

## Abrir no Windows
1. Instale Python 3.10 ou superior e marque **Add Python to PATH**.
2. Extraia o ZIP. Execute **iniciar_windows.bat**. A primeira instalação precisa de internet para baixar pySerial.
3. Abra http://localhost:8765 e mantenha o terminal aberto.
4. Conecte o ESP32 usando cabo USB de dados. Feche o Monitor Serial da Arduino IDE.
5. Clique **Atualizar portas**, selecione a COM da placa, escolha **115200** e clique **Conectar ESP32**.
6. Aguarde a inicialização da placa. Faça uma sombra ou mude a luz sobre os LDRs e observe as leituras.

Alternativa pelo terminal, nesta pasta:
```sh
python -m pip install -r requirements.txt
python app.py
```

## O que aparece
- Quatro sensores: **superior (GPIO 3), esquerdo (GPIO 4), direito (GPIO 1), inferior (GPIO 0)**. São direções, não quatro cantos.
- Leituras reais do ADC de 12 bits (0–4095). O firmware faz média de 8 amostras. Não são lux, tensão nem energia gerada.
- Erros DifH e DifV conforme transmitidos pelo firmware, com 3 casas decimais.
- **Erro H = ln(esquerdo+1) − ln(direito+1)**, com bias zero. **Erro V = ln(superior+1) − ln(inferior+1)**.
- Condição por eixo calculada com as leituras brutas e precisão completa, evitando classificar incorretamente erros arredondados para 0,300. Tolerância: módulo do erro **até 0,30**. Não são graus nem diferença ADC de 30.
- Luz suficiente em H quando esquerdo OU direito é **maior que 50**. Em V, superior OU inferior deve ser maior que 50. Erro elevado no escuro não deve aparecer como necessidade de correção.
- Ângulo vertical é o **comando do firmware**, limitado a 5°–175°, passo 2°. Não é posição medida.
- Horizontal é **servo contínuo** (GPIO 7); os comandos 88, 95 e 103 não medem posição. A interface indica “Contínuo”. Servo vertical: GPIO 6.
- A saída serial ocorre depois do pulso horizontal e do comando de parada. Não informa direção executada, duração do pulso, lastDirH, holdAte ou movimento físico. O dashboard não inventa esses estados. Erro acima do limite pode coexistir com pausa de alinhamento; não implica pulso naquele ciclo.
- Sem nova leitura por 3 segundos: dados explicitamente desatualizados. O firmware continua controlando o protótipo independentemente do dashboard.

Os pinos acima vêm do código enviado. Esta atualização não altera ligações, modelo da placa ou controle físico. Não houve acesso ao hardware para testar em bancada.

## Comunicação
A integração pronta é USB serial. O firmware atual fornecido não contém Bluetooth nem Wi-Fi. A instalação de um dashboard não ativa essas funções na placa.

Se o grupo implementar Bluetooth clássico/SPP e imprimir a mesma linha por essa conexão, é possível usar sua COM no computador. BLE não é suportado. Confirme a arquitetura com o professor caso o grupo queira comunicação sem fio. Documentação do leitor de portas: https://pyserial.readthedocs.io/en/latest/tools.html.

## Dois testes obrigatórios
**01 — Condição normal:** iluminar de maneira semelhante os sensores opostos, acima de 50 ADC. Esperado: erros dentro de ±0,30 e vertical estável depois do ajuste. Observar o horizontal fisicamente; a serial não comprova seu movimento ou sua parada.

**02 — Condição de ajuste:** criar sombra ou iluminar um lado. Esperado: diferença logarítmica maior que 0,30 em módulo, com luz suficiente no eixo; observar a resposta do servo correspondente. O horizontal pode fazer pulsos ou entrar na pausa de 1 segundo após inversão de erro. O vertical pode chegar ao limite de curso. Registrar o resultado observado, sem assumir que todo erro implica movimento imediato.

**Opcional — pouca luz:** ambos os sensores do eixo até 50. Esperado: luz insuficiente no dashboard; o código não inicia correção nesse eixo.

Preencha o responsável, observação física e resultado, e clique **Registrar leitura atual**. Baixe **testes JSON** e **leituras CSV**. O dashboard exige dados recentes para registrar. Não há testes físicos pré-aprovados.

## Evidências para entrega
Faça captura da interface com o indicador de dados reais. Grave o protótipo e a tela enquanto muda a iluminação e observa os servos. Inclua código do dashboard, código completo do ESP32, CSV, JSON, capturas e relatos no diário de bordo. Fotos da construção e desenho da estrutura ficam com os responsáveis por essa parte.

## Arquivos
- app.py: servidor local e recepção serial.
- dashboard.html: interface, gráficos e registro de testes.
- requirements.txt e iniciar_windows.bat: instalação/inicialização.
- telemetria_esp32.ino.txt: notas de compatibilidade; não precisa copiar funções no código atual.
- test_dashboard.py: testes de software.
- registros/leituras_reais_v2.csv: histórico real automático. registros/simulacao_v2.csv: artificial, separado.

A sessão visual mantém até 3.000 leituras; o gráfico mostra as últimas 120. O CSV automático preserva o histórico adicional. Cada nova conexão limpa a sessão visual sem apagar arquivos. Registros manuais ficam no navegador; exporte-os em JSON para enviar ao professor.

**Explorar simulação** serve para conhecer a tela; não comprova integração. Sua origem fica marcada. A simulação não reproduz toda a dinâmica dos pulsos do firmware.

Se a COM estiver ocupada, feche o Monitor Serial. Se não aparecer, verifique cabo de dados e driver da placa. Se houver linhas inválidas, confira baud 115200 e formato. Abrir a serial pode reiniciar a placa; aguarde.

## Validação
Testes de software incluem formato serial atualizado, quatro sensores por direção, pouca luz, limiar, erros logarítmicos, ângulo vertical e compatibilidade com formatos anteriores. A integração física precisa ser validada pelo grupo.
