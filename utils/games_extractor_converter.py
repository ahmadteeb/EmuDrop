import os
import subprocess
from utils.logger import logger
from utils.config import Config
import shutil

class GamesExtractorConverter:
    def __init__(self, status, game_prop, download_path) -> None:
        self.platform_id = game_prop.platform_id
        self.download_path = download_path
        self.rom_path = os.path.join(os.environ['ROMS_DIR'], game_prop.platform_id)
        self.isExtractable = game_prop.isExtractable
        self.canBeRenamed = game_prop.canBeRenamed
        self.game_name = game_prop.name
        self.process = None
        self.callback = None        # Callback function for progress updates
        self.status = status
        self.cancelled = False
    
    def _run_command(self, cmd, operation_name=""):
        """Run a command and update progress information.
        
        Args:
            cmd: Command to execute as list of arguments
            operation_name: Name of the operation for progress tracking
            
        Returns:
            tuple: (success, error_message)
            
        Raises:
            RuntimeError: If the command fails to execute
        """
        if self.cancelled:
            raise RuntimeError("Operation cancelled")
            
        self.status['current_operation'] = operation_name
        try:
            process = subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            self.process = process
            
            stdout, stderr = process.communicate()
            
            if self.cancelled:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                raise RuntimeError("Operation cancelled")
            
            if process.returncode != 0:
                error_msg = f"{operation_name}: Command failed with return code {process.returncode}"
                if stderr:
                    error_msg += f"\n{stderr}"
                if stdout:
                    error_msg += f"\n{stdout}"
                return False, error_msg
                
            return True, stdout
            
        except Exception as e:
            if self.cancelled:
                raise RuntimeError("Operation cancelled")
            return False, str(e)
        finally:
            self.process = None
        
    def cancel(self):
        """Cancel the current operation"""
        self.cancelled = True
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        
    def move_game(self):
        files_path, files = self.scan_folder(self.download_path)
        output_path = os.path.join(files_path, "output")
        os.makedirs(output_path, exist_ok=True)

        game_names_to_scrape = []
        valid_files = [f for f in files if not f.endswith(('.nfo', '.html', '.htm'))]

        def clean_stem(filename):
            return os.path.splitext(os.path.splitext(filename)[0])[0]

        def _normal_game_out():
            rename = len(valid_files) == 1
            for file in valid_files:
                game_name = clean_stem(file)
                
                # temp commented
                # if rename and self.canBeRenamed:
                #     game_name = os.path.splitext(self.game_name)[0]
                
                ext = os.path.splitext(file)[1]
                dest_file = f"{game_name}{ext}"
                os.replace(os.path.join(files_path, file), os.path.join(output_path, dest_file))
                game_names_to_scrape.append(dest_file)

        def _convert_file(input_file, converter_type):
            game_name = clean_stem(input_file)
            
            conversion_commands = {
                'chd': [
                    f"{os.environ['EXECUTABLES_DIR']}/chdman",
                    "createcd",
                    "-i", os.path.join(files_path, input_file),
                    "-o", os.path.join(output_path, f"{game_name}.chd"),
                    "-c", "zlib"
                ],
                'cue': [
                    f"{os.environ['EXECUTABLES_DIR']}/ccd2cue",
                    os.path.join(files_path, input_file),
                    "-o", os.path.join(files_path, f"{game_name}.cue")
                ],
                'bin': [
                    f"{os.environ['EXECUTABLES_DIR']}/ecm2bin",
                    os.path.join(files_path, input_file),
                    os.path.join(files_path, f"{game_name}.bin")
                ]
            }
            
            if converter_type in conversion_commands:
                operation_name = f"Converting to {converter_type.upper()}"
                logger.info(operation_name)
                success, result = self._run_command(
                    conversion_commands[converter_type],
                    operation_name
                )
                
                if not success:
                    raise RuntimeError(result)
                    
                if converter_type == 'chd':
                    game_names_to_scrape.append(game_name)
                    logger.info(f"File {input_file} has been converted to CHD successfully")

        # Platforms requiring CHD conversion
        to_chd_platforms = ['SEGACD', 'DC', 'PANASONIC', 'PS', 'NAOMI', 'PCFX', 'PCECD', 'SATURN']
        if self.platform_id in to_chd_platforms:
            # Group files by extension for batch processing
            file_groups = {
                'ccd': [f for f in files if f.lower().endswith('.ccd')],
                'ecm': [f for f in files if f.lower().endswith('.ecm')],
                'img': [f for f in files if f.lower().endswith('.img')]
            }
            
            # Process each group of files
            for ext, conv_files in file_groups.items():
                for file in conv_files:
                    if ext == 'ccd':
                        _convert_file(file, 'cue')
                    elif ext == 'ecm':
                        _convert_file(file, 'bin')
                    elif ext == 'img':
                        new_file_name = f"{clean_stem(file)}.bin"
                        shutil.copyfile(os.path.join(files_path, file), os.path.join(files_path, new_file_name))
                        
            # Convert all intermediate files to CHD
            intermediate_files = [f for f in os.listdir(files_path) 
                               if f.lower().endswith(('.cue', '.gdi'))]
            for file in intermediate_files:
                _convert_file(file, 'chd')
                
            # If no CHD files were created, fall back to normal processing
            if not any(f.lower().endswith('.chd') for f in os.listdir(output_path)):
                _normal_game_out()
        else:
            _normal_game_out()
            
        # Final move to ROM path
        self.status['current_operation'] = "Moving to ROM directory"
        output_files = os.listdir(output_path)
        if output_files:
            os.makedirs(self.rom_path, exist_ok=True)
            for file in output_files:
                os.replace(
                    os.path.join(output_path, file),
                    os.path.join(self.rom_path, file)
                )
                
        return list(set(game_names_to_scrape))
                
    def scan_folder(self, subfolder):
        # Handle nested folders
        files = os.listdir(subfolder)
        if files and os.path.isdir(os.path.join(subfolder, files[0])):
            subfolder = os.path.join(subfolder, files[0])
                
        # Check for archive files
        archive_files = [file for file in os.listdir(subfolder) if any(ext in file.lower() for ext in ['.zip', '.rar', '.7z'])]
        if archive_files:
            if not self.isExtractable:
                return subfolder, archive_files
            
            else:
                tmp_path = os.path.join(subfolder, 'tmp')
                os.makedirs(tmp_path, exist_ok=True)
                self.extractor(os.path.join(subfolder, archive_files[0]), tmp_path)
                return self.scan_folder(tmp_path)
        else:
            return subfolder, os.listdir(subfolder)
    
    def extractor(self, file, extract_to):
        """Extract an archive file to the specified directory.
        
        Args:
            file: Path to the archive file
            extract_to: Directory to extract to
            
        Raises:
            FileNotFoundError: If the archive file doesn't exist
            RuntimeError: If extraction fails
        """
        if not os.path.exists(file):
            error_msg = f"Archive file not found: {file}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)
            
        self.status['current_operation'] = "Extracting archive"
        logger.info(f"Extracting {file}...")
        
        success, result = self._run_command(
            [f"{os.environ['EXECUTABLES_DIR']}/7z", "x", file, f'-o{str(extract_to)}'],
            "Extracting"
        )
        
        if not success:
            error_msg = f"Failed to extract {file}\n{result}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        os.remove(file)
        logger.info(f"File {file} has been extracted successfully")
        