package crylogger;

public class Template {

	public void execute(boolean fail) throws Exception {		
		if(fail) {
			executeFail();
		} else {
			executeSuccess();
		}		
	}
	
	private void executeSuccess() throws Exception {
		
	}
	
	private void executeFail() throws Exception {
		
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new Template().execute(fail);		
	}

}
