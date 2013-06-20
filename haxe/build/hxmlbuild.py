import os
import re
import time
import sublime

from haxe import config
from haxe import types as hxtypes
from haxe import panel as hxpanel
from haxe.tools import hxsrctools


from haxe.execute import run_cmd, run_cmd_async
from haxe.log import log


class HxmlBuild :

	def __init__(self, hxml, build_file) :
		
		self.show_times = False
		self.std_bundle = hxsrctools.empty_type_bundle()
		self.args = []
		self.main = None
		self.target = None
		self.output = "dummy.js"
		self.hxml = hxml
		self._build_file = build_file
		self.classpaths = []
		self.libs = []
		self.type_bundle = None
		self._update_time = None
		self.mode_completion = False
		self.defines = []
		

	@property
	def title(self):
		return self.output

	@property
	def build_file(self):
		return self._build_file

	def add_define (self, define):
		self.defines.append(define)
		
	
	def set_main(self, main):
		self.main = main
	
	def get_name (self):
		return "[No Main]" if self.main == None else self.main

	def set_std_bundle(self, std_bundle):
		self.std_bundle = std_bundle

	
	def equals (self, other):
		
		return (self.args == other.args 
			and self.main == other.main
			and self.target == other.target
			and self.output == other.output
			and self.hxml == other.hxml
			and self.classpaths == other.classpaths
			and self.libs == other.libs
			and self.show_times == other.show_times
			and self.mode_completion == other.mode_completion
			and self.defines == other.defines
			and self._build_file == other._build_file)
		   
	
	def copy (self):

		self.get_types()

		hb = HxmlBuild(self.hxml, self.build_file)
		hb.args = list(self.args)
		hb.main = self.main
		hb.target = self.target
		hb.output = self.output
		hb.defines = list(self.defines)
		hb.std_bundle = self.std_bundle
		hb.classpaths = list(self.classpaths)
		hb.libs = list(self.libs)
		hb.type_bundle = self.type_bundle
		hb._update_time = self._update_time
		hb.show_times = self.show_times
		hb.mode_completion = self.mode_completion
		return hb

	def add_arg(self, arg):
		self.args.append(arg)

	def get_build_folder (self):
		return os.path.dirname(self.build_file) if self.build_file is not None else None

	def set_build_cwd (self):
		self.set_cwd(self.get_build_folder())
	
	def align_drive_letter(self, path):
		is_win =  sublime.platform() == "windows"
		
		if is_win:
			reg = re.compile("^([a-z]):(.*)$")
			match = re.match(reg, path)
			if match is not None:
				path = match.group(1).upper() + ":" + match.group(2)
		return path

	def add_classpath (self, cp):
		cp = self.align_drive_letter(cp)
		
		self.classpaths.append(cp)
		self.args.append(("-cp", cp))
	

	def add_lib(self, lib):
		self.libs.append(lib)
		self.add_arg( ("-lib", lib.name))

	def get_classpath_of_file (self, file):
		
		file = self.align_drive_letter(file)
		
		cps = list(self.classpaths)

		cps.append(self.get_build_folder())
		for cp in cps:
			prefix = os.path.commonprefix([cp, file])
			if prefix == cp:
				return cp

		return None

	def is_file_in_classpath (self, file):
		file = self.align_drive_letter(file)
		return self.get_classpath_of_file(file) is not None

	def get_relative_path (self, file):
		
		file = self.align_drive_letter(file)

		cp = self.get_classpath_of_file(file)

		return file.replace(cp, "")[1:] if cp is not None else None

	def target_to_string (self):
		if self.target is None:
			target = "js"
		else:
			target = self.target
			if target == "js" and "nodejs" in self.defines:
				target = "node.js"
		return target

	def to_string(self) :
		out = os.path.basename(self.output)
		
		return "{main} ({target} - {out})".format(self=self, out=out, main=self.get_name(), target=self.target_to_string());
	
	def make_hxml( self ) :
		outp = "# Autogenerated "+self.hxml+"\n\n"
		outp += "# "+self.to_string() + "\n"
		outp += "-main "+ self.main + "\n"
		for a in self.args :
			outp += " ".join( list(a) ) + "\n"
		
		d = os.path.dirname( self.hxml ) + "/"
		
		# relative paths
		outp = outp.replace( d , "")
		outp = outp.replace( "-cp "+os.path.dirname( self.hxml )+"\n", "")

		outp = outp.replace("--no-output " , "")
		outp = outp.replace("-v" , "")

		outp = outp.replace("dummy" , self.main.lower() )

		return outp.strip()

	def set_cwd (self, cwd):
		self.args.append(("--cwd" , cwd ))

	def set_times (self):
		self.show_times = True
		self.args.append(("--times", ""))
		self.args.append(("-D", "macro-times"))
		self.args.append(("-D", "macro_times"))

	def set_server_mode (self, server_port = 6000):
		self.args.append(("--connect" , str(server_port)))

	def get_command_args (self, haxe_path):
		cmd = list(haxe_path)

		for a in self.args :
			cmd.extend( list(a) )

		for l in self.libs :
			cmd.append( "-lib" )
			cmd.append( l.as_cmd_arg() )

		if self.main != None:
			cmd.append("-main")
			cmd.append(self.main)
		return cmd

	def set_auto_completion (self, display, macro_completion = False, no_output = True):
		
		self.mode_completion = True

		args = self.args

		self.main = None

		def filterTargets (x):
			return x[0] != "-cs" and x[0] != "-x" and x[0] != "-js" and x[0] != "-php" and x[0] != "-cpp" and x[0] != "-swf" and x[0] != "-java"

		if macro_completion:
			args = list(filter(filterTargets, args ))
		else:
			args = list(map(lambda x : ("-neko", x[1]) if x[0] == "-x" else x, args))

		def filter_commands_and_dce (x):
			return x[0] != "-cmd" and x[0] != "-dce"



		args = list(filter(filter_commands_and_dce, args ))

		if not self.show_times:
			def filter_times (x):
				return x[0] != "--times"
			args = list(filter(filter_times, args))

		if (macro_completion) :
			args.append(("-neko", "__temp.n"))

		
		args.append( ("--display", display ) )
		if (no_output):
			args.append( ("--no-output" , "") )

		self.args = args


	def _update_types(self):

		#haxe.output_panel.HaxePanel.status("haxe-debug", "updating types")
		log("update types for classpaths:" + str(self.classpaths))
		log("update types for libs:" + str(self.libs))
		self.type_bundle = hxtypes.find_types(self.classpaths, self.libs, self.get_build_folder(), [], [], include_private_types = False )

		


	def _should_refresh_types(self, now):
		
		# if self._update_time is not None:
		# 	log("update_diff:" + str(now - self._update_time))
		# 	log("update_diff:" + str((now - self._update_time > 100)))
		return self.type_bundle is None or self._update_time is None or (now - self._update_time) > 10

	def get_types( self ) :
		now = time.time()
		
		if self._should_refresh_types(now):
			log("UPDATE THE TYPES NOW")
			self._update_time = now
			self._update_types()

		return self.type_bundle

	def prepare_check_cmd(self, project, server_mode, view):
		cmd, build_folder = self.prepare_build_cmd(project, server_mode, view)
		cmd.append("--no-output")
		return cmd, build_folder
	
	def prepare_run_cmd (self, project, server_mode, view):
		cmd, build_folder, nekox_file = self._prepare_run(project, view, server_mode)

		if sublime.platform() == "linux":
			default_open_ext = "xdg-open"

		if nekox_file != None:
			cmd.extend(["-cmd", "neko " + nekox_file])
		elif self.target == "swf" and default_open_ext != None:
			cmd.extend(["-cmd", default_open_ext + " " + self.output])
		elif self.target == "neko":
			cmd.extend(["-cmd", "neko " + self.output])
		elif self.target == "cpp":
			cmd.extend(["-cmd", os.path.join(self.output,self.main) + "-debug"])
		elif self.target == "js" and "nodejs" in self.defines:
			cmd.extend(["-cmd", "nodejs " + self.output])
		elif self.target == "java":
			sep_index = self.output.rfind(os.path.sep)
			jar = self.output + ".jar" if sep_index == -1 else self.output[sep_index+1:] + ".jar"
			cmd.extend(["-cmd", "java -jar " + os.path.join(self.output, jar)])
		elif self.target == "cs":
			cmd.extend(["-cmd", "cd " + self.output])
			cmd.extend(["-cmd", "gmcs -recurse:*.cs -main:" + self.main + " -out:" + self.main + ".exe-debug"])
			cmd.extend(["-cmd", os.path.join(".", self.main + ".exe-debug")])

		return cmd, build_folder

	def prepare_build_cmd (self, project, server_mode, view):
		cmd, build_folder,_ = self._prepare_run(project, view, server_mode)
		return (cmd, build_folder)

	def _prepare_run (self, project, view, server_mode = None):

		server_mode = project.server_mode if server_mode is None else server_mode
		
		run_exec = self._get_run_exec(project, view)
		b = self.copy()
		
		nekox_file_name = None
		
		for i in range(0, len(b.args)):
			a = b.args[i]
			if a[0] == "-x":
				nekox_file_name = a[1] + ".n"
				b.args[i] = ("-neko", nekox_file_name)

		if server_mode:
			project.start_server( view )
			b.set_server_mode(project.server.get_server_port())

		
		b.set_build_cwd()
		cmd = b.get_command_args(run_exec)

		return (cmd, self.get_build_folder(), nekox_file_name)

	def _get_run_exec(self, project, view):
		return project.haxe_exec(view)

	def _run_async (self, project, view, callback):

		env = project.haxe_env(view)
		cmd, build_folder, nekox_file_name = self._prepare_run(project, view)
		
		def cb (out, err):
			self._on_run_complete(out, err, build_folder, nekox_file_name)
			callback(out, err)

		run_cmd_async( args=cmd, input="", cwd=build_folder, env=env, callback=cb )
	
	

	def _run_sync (self, project, view):
		
		env = project.haxe_env(view)
		cmd, build_folder, nekox_file_name = self._prepare_run(project, view)
			
		out, err = run_cmd( args=cmd, input="", cwd=build_folder, env=env )
		
		self._on_run_complete(out, err, build_folder, nekox_file_name)
		
		return out,err


	def _on_run_complete(self, out, err, build_folder, nekox_file_name):
		log("---------------cmd-------------------")
		log("out:" + out)
		log("err:" + err)
		log("---------compiler-output-------------")
		if nekox_file_name is not None:
			self._run_neko_x(build_folder, nekox_file_name)
		

	def _run_neko_x(self, build_folder, neko_file_name):
		neko_file = os.path.join(build_folder, neko_file_name)
		log("run nekox: " + neko_file) 
		out, err = run_cmd(["neko", neko_file])
		hxpanel.default_panel().writeln(out)
		hxpanel.default_panel().writeln(err)

	def run(self, project, view, async, callback):
		if async:
			log("RUN ASYNC COMPLETION")
			self._run_async( project, view, callback )
		else:
			log("RUN SYNC COMPLETION")
			out, err = self._run_sync( project, view )
			callback(out, err)

	def is_type_available (self, type):
		pack = type.toplevel_pack
		return pack is None or self.is_pack_available(pack)


	def is_pack_available (self, pack):
		if pack == "":
			return True

		pack = pack.split(".")[0]
		target = self.target

		available = True

		if pack is not None and target is not None and pack in config.target_packages:
			if target in config.target_std_packages:
				if pack not in config.target_std_packages[target]:
					available = False;
		return available
