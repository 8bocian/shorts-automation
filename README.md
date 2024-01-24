# Youtube Shorts Creator

This Python program is designed to create short videos. It utilizes several API keys and environment variables for smooth functionality.

## Environment Variables

Before running the program, make sure to set up the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key for accessing OpenAI services.
- `ELEVENLABS_API_KEY`: API key for Eleven Labs integration.
- `STABLEDIFFUSION_API_KEY`: API key for Stable Diffusion service.
- `DATABASE_URI`: URI for the database used by the program.
- `CERT`: Certificate information (if applicable).
- `DECRYPTED_KEY`: Decrypted key for secure communication.
- `MUSIC_PATH`: Path to the directory containing music files.
- `FFMPEG_PATH`: Path to the FFMPEG executable.

## Getting Started

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:

    ```bash
    export OPENAI_API_KEY=your_openai_key
    export ELEVENLABS_API_KEY=your_elevenlabs_key
    export STABLEDIFFUSION_API_KEY=your_stablediffusion_key
    export DATABASE_URI=your_database_uri
    export CERT=ssl_file_path
    export DECRYPTED_KEY=ssl_key_path
    export MUSIC_PATH=your_music_path
    export FFMPEG_PATH=your_ffmpeg_path
    ```

4. Run the program:

    ```bash
    python app.py
    ```

## Notes

- Make sure you have a stable internet connection before running the program.
- Check the documentation for each API/service to understand their usage and limitations.
  
## License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for more information.
