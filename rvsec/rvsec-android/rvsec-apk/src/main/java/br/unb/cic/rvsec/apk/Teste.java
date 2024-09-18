package br.unb.cic.rvsec.apk;

import java.io.IOException;

import org.xmlpull.v1.XmlPullParserException;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;

public class Teste {

	private AppInfo execute(String apk) throws IOException, XmlPullParserException {
		return AppReader.readApk(apk);
	}

	public static void main(String[] args) {
		String baseDir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/";
		String apk = baseDir + "cryptoapp.apk";

		Teste teste = new Teste();
		try {
			AppInfo info = teste.execute(apk);
			System.out.println(info);
		} catch (IOException | XmlPullParserException e) {
			e.printStackTrace();
		}
	}

}
