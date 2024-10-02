package br.unb.cic.rvsec.reach.writer;

public class WriterFactory {

	public static Writer fromType(WriterType type) {
		if(WriterType.json.equals(type)) {
			return jsonWriter();
		}
		return csvWriter();
	}
	
	public static Writer defaultWriter() {
		return csvWriter();
	}

	public static Writer csvWriter() {
		return new CsvWriter();
	}

	public static Writer jsonWriter() {
		return new JsonWriter();
	}

}
