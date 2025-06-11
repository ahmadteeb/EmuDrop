import os
import subprocess
from utils.logger import logger
from utils.config import Config
import shutil
import re

class GamesExtractorConverter:
    def __init__(self, status, game_prop, download_path) -> None:
        self.platform_id = game_prop.platform_id
        self.download_path = download_path
        self.rom_path = os.path.join(os.environ['ROMS_DIR'], Config.SYSTEMS_MAPPING[game_prop.platform_id])
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
            shell = False
            # if windows remove ./ and set shell to True
            if os.name == 'nt':
                cmd[0] = cmd[0].replace('./', '')
                shell = True
                
            process = subprocess.Popen(
                cmd,
                cwd=os.environ['EXECUTABLES_DIR'],
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=shell
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
    
    def _trim_file_name(self, input_file):
        # This removes things like .img.iso.zip etc
        file_name = re.sub(r'(\.[a-zA-Z0-9]+)+$', '', input_file)
        return file_name
        
    def move_game(self):
        files_path, files = self.scan_folder(self.download_path)
        output_path = os.path.join(files_path, "output")
        os.makedirs(output_path, exist_ok=True)

        game_names_to_scrape = []
        valid_files = [f for f in files if not f.endswith(('.nfo', '.html', '.htm'))]
           
        def _normal_game_out():
            rename = len(valid_files) == 1
            for file in valid_files:
                game_name = self._trim_file_name(file)
                
                # temp commented
                # if rename and self.canBeRenamed:
                #     game_name = os.path.splitext(self.game_name)[0]
                
                _, ext = os.path.splitext(file)
                dest_file = f"{game_name}{ext}"
                os.replace(os.path.join(files_path, file), os.path.join(output_path, dest_file))
                game_names_to_scrape.append(dest_file)

        def _convert_file(input_file, converter_type):
            game_name = self._trim_file_name(input_file)
            
            conversion_commands = {
                'chd': [
                    "./chdman",
                    "createcd",
                    "-i", os.path.join(files_path, input_file),
                    "-o", os.path.join(output_path, f"{game_name}.chd"),
                    "-c", "zlib"
                ],
                'cue': [
                    "./ccd2cue",
                    os.path.join(files_path, input_file),
                    "-o", os.path.join(files_path, f"{game_name}.cue")
                ],
                'bin': [
                    "./ecm2bin",
                    os.path.join(files_path, input_file),
                    os.path.join(files_path, f"{game_name}.bin")
                ]
            }
            
            if converter_type in conversion_commands:
                operation_name = f"Converting to {converter_type.upper()}"
                logger.info(f"{operation_name}: {input_file}")
                success, result = self._run_command(
                    conversion_commands[converter_type],
                    operation_name
                )
                
                if not success:
                    raise RuntimeError(result)
                    
                if converter_type == 'chd':
                    game_names_to_scrape.append(f"{game_name}.chd")
                    logger.info(f"File {input_file} has been converted to CHD successfully")

        # Platforms requiring CHD conversion
        to_chd_platforms = ['SEGACD', 'DC', 'PANASONIC', 'PS', 'NAOMI', 'PCFX', 'PCECD', 'SATURN']
        if self.platform_id in to_chd_platforms:
            # Group files by extension for batch processing
            file_groups = {
                'bin': [f for f in files if f.lower().endswith('.bin')],
                'img': [f for f in files if f.lower().endswith('.img')],
                'ecm': [f for f in files if f.lower().endswith('.ecm')],
                'ccd': [f for f in files if f.lower().endswith('.ccd')],
                'cue': [f for f in files if f.lower().endswith('.cue')],
            }
            
            # Process each group of files
            for ext, conv_files in file_groups.items():
                for file in conv_files:
                    if ext == 'ccd':
                        _convert_file(file, 'cue')
                    elif ext == 'ecm':
                        _convert_file(file, 'bin')
                    elif ext == 'cue':
                        input_file_path = os.path.join(files_path, file)
                        output_file_path = os.path.join(files_path, f"{self._trim_file_name(file)}.cue")
                        with open(input_file_path, 'r') as f:
                            content = f.readlines()
                        
                        bin_name_line = content[0].split('"')
                        bin_name_line[1] = f"{self._trim_file_name(file)}.bin"
                        content[0] = '"'.join(bin_name_line)
                        
                        os.remove(input_file_path)
                        with open(output_file_path, 'w') as f:
                            f.writelines(content)
                            
                    elif ext in ['bin', 'img']:
                        new_file_name = f"{self._trim_file_name(file)}.bin"
                        if not os.path.exists(os.path.join(files_path, new_file_name)):
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
            ["./7z", "x", file, f'-o{str(extract_to)}'],
            "Extracting"
        )
        
        if not success:
            error_msg = f"Failed to extract {file}\n{result}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        os.remove(file)
        logger.info(f"File {file} has been extracted successfully")