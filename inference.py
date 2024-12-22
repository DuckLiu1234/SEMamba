import glob
import os
import argparse
import json
import torch
import librosa
import soundfile as sf
from models.stfts import mag_phase_stft, mag_phase_istft
from models.generator import SEMamba
from models.pcs400 import cal_pcs

from utils.util import (
    load_ckpts, load_optimizer_states, save_checkpoint,
    build_env, load_config, initialize_seed, 
    print_gpu_info, log_model_info, initialize_process_group,
)

# Global variables
model = None
device = None
cfg = None

def initialize_model(config_path, checkpoint_path):
    """Initialize the SEMAMBA model"""
    global model, device, cfg
    
    if torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        raise RuntimeError("Currently, CPU mode is not supported.")
    
    cfg = load_config(config_path)
    model = SEMamba(cfg).to(device)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict['generator'])
    model.eval()

def process_audio(input_path, output_path, use_pcs=False):
    """Process a single audio file"""
    global model, device, cfg
    
    if model is None:
        raise RuntimeError("Model not initialized. Call initialize_model first.")
    
    n_fft = cfg['stft_cfg']['n_fft']
    hop_size = cfg['stft_cfg']['hop_size']
    win_size = cfg['stft_cfg']['win_size']
    compress_factor = cfg['model_cfg']['compress_factor']
    sampling_rate = cfg['stft_cfg']['sampling_rate']
    
    with torch.no_grad():
        # Load and convert to mono if necessary
        noisy_wav, _ = librosa.load(input_path, sr=sampling_rate, mono=True)
        noisy_wav = torch.FloatTensor(noisy_wav).to(device)
        
        # Normalize
        norm_factor = torch.sqrt(len(noisy_wav) / torch.sum(noisy_wav ** 2.0)).to(device)
        noisy_wav = (noisy_wav * norm_factor).unsqueeze(0)
        
        # Process
        noisy_amp, noisy_pha, noisy_com = mag_phase_stft(noisy_wav, n_fft, hop_size, win_size, compress_factor)
        amp_g, pha_g, com_g = model(noisy_amp, noisy_pha)
        audio_g = mag_phase_istft(amp_g, pha_g, n_fft, hop_size, win_size, compress_factor)
        audio_g = audio_g / norm_factor
        
        # Post-process and save
        if use_pcs:
            audio_g = cal_pcs(audio_g.squeeze().cpu().numpy())
        else:
            audio_g = audio_g.squeeze().cpu().numpy()
            
        sf.write(output_path, audio_g, sampling_rate, 'PCM_16')
        
        return output_path

def inference(args, device):
    """Original inference function for backward compatibility"""
    cfg = load_config(args.config)
    model = SEMamba(cfg).to(device)
    state_dict = torch.load(args.checkpoint_file, map_location=device)
    model.load_state_dict(state_dict['generator'])

    os.makedirs(args.output_folder, exist_ok=True)
    model.eval()

    with torch.no_grad():
        for i, fname in enumerate(os.listdir(args.input_folder)):
            input_path = os.path.join(args.input_folder, fname)
            output_path = os.path.join(args.output_folder, fname)
            process_audio(input_path, output_path, args.post_processing_PCS)

def main():
    print('Initializing Inference Process..')
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', default='/mnt/e/Corpora/noisy_vctk/noisy_testset_wav_16k/')
    parser.add_argument('--output_folder', default='results')
    parser.add_argument('--config', default='results')
    parser.add_argument('--checkpoint_file', required=True)
    parser.add_argument('--post_processing_PCS', default=False)
    args = parser.parse_args()

    global device
    if torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        raise RuntimeError("Currently, CPU mode is not supported.")

    inference(args, device)

if __name__ == '__main__':
    main()
