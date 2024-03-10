import matplotlib.pyplot as plt
import numpy as np

# Dados
t = np.linspace(-1, 6, 1000)
y1 = np.sin(t)
y2 = np.sin(t - 1)
y3 = np.sin(t + 1)

# Plotando as funções
plt.figure(figsize=(8, 5))
plt.plot(t, y1, label='Sin(t)', color='green')
plt.plot(t, y2, label='Sin(t-1)', color='red')
plt.plot(t, y3, label='Sin(t+1)', color='blue')

# Títulos, labels e outras configurações
plt.title("Deslocamento temporal")
plt.xlabel("Tempo [s]")
plt.ylabel("Amplitude")
plt.grid(True)
plt.legend()
plt.ylim([-1.1, 1.1])
plt.xlim([-1, 6])
plt.axhline(0, color='black', linewidth=0.5)  # Eixo X
plt.axvline(0, color='black', linewidth=0.5)  # Eixo Y

plt.tight_layout()
plt.show()
