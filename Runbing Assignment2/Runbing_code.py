import numpy as np

eta = 0.3
beta1 = 0.9
beta2 = 0.999
epsilon = 0


def AdamOptim(t, dw, m_dw, v_dw):
    # update the first moment estimate
    m_dw = beta1 * m_dw + (1 - beta1) * dw

    # update the second raw moment estimate
    v_dw = beta2 * v_dw + (1 - beta2) * (dw ** 2)

    # bias correction
    m_dw_corr = m_dw / (1 - beta1 ** t)
    v_dw_corr = v_dw / (1 - beta2 ** t)

    res = eta * (m_dw_corr / (np.sqrt(v_dw_corr) + epsilon))
    # print('updated sita',res)
    # update weights and biases
    return m_dw, v_dw, res



def update(h):
    # initial parameters
    m, v, acc, dw = 0, 0, 0, -1
    acc_lis = []
    # set the flag to check whether it pass the X point
    passX_flag = False
    for i in range(1, 100):
        # dw function
        if acc < 1:
            dw = -1
        elif acc > 1 and acc - 1 < h:
            dw = 1
        elif acc - 1 > h:
            dw = -1
        # update the parameters
        m, v, sita = AdamOptim(i, dw, m, v)
        # update the sita
        acc -= sita
        acc_lis.append(round(acc, 3))
        # if pass X,set the flag
        if acc > 1:
            passX_flag = True
        # if the flag is true and  w < 1, stuck!
        if acc < 1 and passX_flag:
            print('h = ' + str(h) + '-stuck at X!-')
            print('Updated w', acc_lis)
            return
        if acc > 1 + 2 * h:
            print('h = ' + str(h) + '-Pass X!-')
            print('Updated w', acc_lis)
            return
    return


for h in range(4100, 4110):
    update(h / 10000)
