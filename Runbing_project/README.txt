There are two folder paths as input:
 training_data and testing_data
 Each folder should contain original data as xxxx_pro_cg_.pdb and yyyy_lig_cg_.pdb

Cooresponding input code is shown:
 read_train_pdb('/training_data/{:04d}_pro_cg.pdb'.format(i))) 
 read_train_pdb('/training_data/{:04d}_lig_cg.pdb'.format(i))) 
 read_train_pdb('/testing_data/{:04d}_pro_cg.pdb'.format(i))) 
 read_train_pdb('/testing_data/{:04d}_lig_cg.pdb'.format(i))) 
