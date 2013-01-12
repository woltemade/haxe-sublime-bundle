import haxe.haxe_complete




import sublime, sublime_plugin
import time





from sublime import Region

import haxe

import os




import haxe.codegen

from haxe.tools import PathTools



class HaxeGetTypeOfExprCommand (sublime_plugin.TextCommand ):
	def run( self , edit ) :
		

		view = self.view
		
		fileName = view.file_name()

		if fileName == None:
			return

		fileName = os.path.basename(view.file_name())

		window = view.window()
		folders = window.folders()
 
		projectDir = folders[0]
		tmpFolder = folders[0] + "/tmp"
		targetFile = folders[0] + "/tmp/" + fileName

		if os.path.exists(tmpFolder):
			PathTools.removeDir(tmpFolder)			
		

		os.makedirs(tmpFolder)
		

		fd = open(targetFile, "w+")
		sel = view.sel()

		word = view.substr(sel[0])



		replacement = "(hxsublime.Utils.getTypeOfExpr(" + word + "))."

		newSel = Region(sel[0].a, sel[0].a + len(replacement))

		print(str(newSel))

		print "do replace"
		view.replace(edit, sel[0], replacement)

		newSel = view.sel()[0]

		view.replace(edit, newSel, word)

		newContent = view.substr(sublime.Region(0, view.size()))
		fd.write(newContent)

		view.run_command("undo")
		#print sel


class HaxeDisplayCompletion( sublime_plugin.TextCommand ):

	def run( self , edit ) :

		def f ():
			view = self.view
			s = view.settings();

			print("run_command: auto_complete")
			view.run_command( "auto_complete" , {
				"api_completions_only" : True,
				"disable_auto_insert" : True,
				"next_completion_if_showing" : True
			} )
		sublime.set_timeout(f, 0)




class HaxeDisplayMacroCompletion( sublime_plugin.TextCommand ):
	
	completions = {}

	def run( self , edit ) :
		print("completing")
		view = self.view
		s = view.settings();
		
		print str(s)

		HaxeDisplayMacroCompletion.completions[view.id()] = time.time()

		view.run_command( "auto_complete" , {
			"api_completions_only" : True,
			"disable_auto_insert" : True,
			"next_completion_if_showing" : True,
			"macroCompletion" : True
		} )

		

class HaxeInsertCompletion( sublime_plugin.TextCommand ):
	
	def run( self , edit ) :
		#print("insert completion")
		view = self.view

		view.run_command( "insert_best_completion" , {
			"default" : ".",
			"exact" : True
		} )

class HaxeSaveAllAndBuild( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		complete = haxe.haxe_complete.HaxeComplete.instance()
		view = self.view
		view.window().run_command("save_all")
		complete.run_build( view )

class HaxeRunBuild( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		complete = haxe.haxe_complete.HaxeComplete.instance()
		view = self.view
		print "do run build"
		complete.run_build( view )


class HaxeSelectBuild( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		print "do select build"
		build_helper = haxe.haxe_complete.HaxeComplete.instance().build_helper
		view = self.view
		
		build_helper.select_build( view )

# called 
class HaxeHint( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		#print("haxe hint")
		
		
		view = self.view
		
		view.run_command('auto_complete', {'disable_auto_insert': True})
		


class HaxeRestartServer( sublime_plugin.WindowCommand ):

	def run( self ) :
		view = sublime.active_window().active_view()
		haxe.haxe_complete.HaxeComplete.instance().stop_server()
		haxe.haxe_complete.HaxeComplete.instance().start_server( view )



class HaxeGenerateUsingCommand( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		print "generate using"
		runner = haxe.codegen.HaxeGenerateImportOrUsing(haxe.haxe_panel.HaxePanel, self.view)
		runner.generate_using(edit)


class HaxeGenerateImportCommand( sublime_plugin.TextCommand ):

	def run( self, edit ) :
		print "generate import"
		runner = haxe.codegen.HaxeGenerateImportOrUsing(haxe.haxe_panel.HaxePanel, self.view);
		runner.generate_import(edit)