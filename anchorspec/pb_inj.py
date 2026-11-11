"""PB-INJ (PROTOCOL_PB_INJ.md): reuse pb_m machinery with the arms locked in the protocol."""
import pb_m
pb_m.ARMS = ['et500+inj_mix_0.25', 'et500']
pb_m.CONFIRMATORY = True
pb_m.OUT = pb_m.P.ROOT / 'results' / 'pb_inj'

if __name__ == '__main__':
    pb_m.main()
